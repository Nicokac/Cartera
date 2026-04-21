from __future__ import annotations

import logging
import numpy as np
import pandas as pd

try:
    from ..clients.market_data import fetch_price_history
except ImportError:
    from clients.market_data import fetch_price_history


logger = logging.getLogger(__name__)


def normalize_technical_overlay(df_tech: pd.DataFrame) -> pd.DataFrame:
    if df_tech is None:
        return pd.DataFrame()
    return df_tech.copy()


def compute_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (ADX, DI+, DI-) using Wilder smoothing."""
    alpha = 1.0 / period
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    raw_dm_plus = high.diff()
    raw_dm_minus = -low.diff()
    dm_plus = raw_dm_plus.where((raw_dm_plus > raw_dm_minus) & (raw_dm_plus > 0), 0.0)
    dm_minus = raw_dm_minus.where((raw_dm_minus > raw_dm_plus) & (raw_dm_minus > 0), 0.0)

    atr = tr.ewm(alpha=alpha, adjust=False).mean()
    di_plus = 100.0 * dm_plus.ewm(alpha=alpha, adjust=False).mean() / atr.replace(0.0, np.nan)
    di_minus = 100.0 * dm_minus.ewm(alpha=alpha, adjust=False).mean() / atr.replace(0.0, np.nan)

    di_sum = (di_plus + di_minus).replace(0.0, np.nan)
    dx = 100.0 * (di_plus - di_minus).abs() / di_sum
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    return adx, di_plus, di_minus


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def build_technical_overlay(
    df_cedears: pd.DataFrame,
    *,
    scoring_rules: dict[str, object] | None = None,
    price_history_out: dict | None = None,
) -> pd.DataFrame:
    if df_cedears is None or df_cedears.empty:
        logger.info("Technical overlay skipped: empty CEDEAR frame")
        return pd.DataFrame()

    scoring_rules = scoring_rules or {}
    tech_rules = scoring_rules.get("technical_overlay", {}) or {}
    period = str(tech_rules.get("history_period", "9mo"))
    interval = str(tech_rules.get("interval", "1d"))
    rows: list[dict[str, object]] = []
    base = df_cedears[["Ticker_IOL", "Ticker_Finviz"]].dropna().drop_duplicates()

    for _, row in base.iterrows():
        ticker_iol = str(row["Ticker_IOL"])
        ticker_finviz = str(row["Ticker_Finviz"])
        try:
            hist = fetch_price_history(ticker_finviz, period=period, interval=interval, auto_adjust=True)
            if hist is None or hist.empty or "Close" not in hist.columns:
                rows.append({"Ticker_IOL": ticker_iol, "Ticker_Finviz": ticker_finviz, "Tech_Trend": "Sin datos"})
                continue

            close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
            if close.empty:
                rows.append({"Ticker_IOL": ticker_iol, "Ticker_Finviz": ticker_finviz, "Tech_Trend": "Close vacío"})
                continue

            if price_history_out is not None:
                price_history_out[ticker_iol] = close.tail(60).tolist()

            last_close = float(close.iloc[-1])
            sma9 = float(close.rolling(9).mean().iloc[-1]) if len(close) >= 9 else np.nan
            sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else np.nan
            sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else np.nan
            sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else np.nan
            ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1]) if len(close) >= 20 else np.nan
            ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1]) if len(close) >= 50 else np.nan
            rsi14 = float(compute_rsi(close, 14).iloc[-1]) if len(close) >= 20 else np.nan
            returns = close.pct_change().dropna()
            vol20 = float(returns.tail(20).std() * np.sqrt(252) * 100) if len(returns) >= 20 else np.nan
            volume = pd.to_numeric(hist["Volume"], errors="coerce").dropna() if "Volume" in hist.columns else pd.Series(dtype=float)
            avg_volume_20d = float(volume.tail(20).mean()) if len(volume) >= 20 else np.nan
            volume_last = float(volume.iloc[-1]) if not volume.empty else np.nan
            relative_volume = float(volume_last / avg_volume_20d) if pd.notna(avg_volume_20d) and avg_volume_20d > 0 and pd.notna(volume_last) else np.nan
            return_1d = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) >= 2 else np.nan
            open_s = pd.to_numeric(hist["Open"], errors="coerce") if "Open" in hist.columns else pd.Series(dtype=float)
            return_intraday = float((close.iloc[-1] / open_s.iloc[-1] - 1) * 100) if not open_s.empty and pd.notna(open_s.iloc[-1]) and open_s.iloc[-1] != 0 else np.nan

            has_hl = "High" in hist.columns and "Low" in hist.columns
            if has_hl and len(close) >= 28:
                high_s = pd.to_numeric(hist["High"], errors="coerce")
                low_s = pd.to_numeric(hist["Low"], errors="coerce")
                adx_s, di_plus_s, di_minus_s = compute_adx(high_s, low_s, close)
                adx14 = float(adx_s.iloc[-1]) if pd.notna(adx_s.iloc[-1]) else np.nan
                di_plus14 = float(di_plus_s.iloc[-1]) if pd.notna(di_plus_s.iloc[-1]) else np.nan
                di_minus14 = float(di_minus_s.iloc[-1]) if pd.notna(di_minus_s.iloc[-1]) else np.nan
            else:
                adx14 = di_plus14 = di_minus14 = np.nan
            momentum_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) >= 21 else np.nan
            momentum_60d = float((close.iloc[-1] / close.iloc[-61] - 1) * 100) if len(close) >= 61 else np.nan
            max_3m = float(close.tail(63).max()) if len(close) >= 20 else np.nan
            min_3m = float(close.tail(63).min()) if len(close) >= 20 else np.nan
            high_52w = float(close.tail(252).max()) if len(close) >= 20 else np.nan
            low_52w = float(close.tail(252).min()) if len(close) >= 20 else np.nan
            drawdown = float((last_close / max_3m - 1) * 100) if pd.notna(max_3m) and max_3m != 0 else np.nan
            dist_sma20 = ((last_close / sma20) - 1) * 100 if pd.notna(sma20) and sma20 != 0 else np.nan
            dist_sma50 = ((last_close / sma50) - 1) * 100 if pd.notna(sma50) and sma50 != 0 else np.nan
            dist_sma200 = ((last_close / sma200) - 1) * 100 if pd.notna(sma200) and sma200 != 0 else np.nan
            dist_ema20 = ((last_close / ema20) - 1) * 100 if pd.notna(ema20) and ema20 != 0 else np.nan
            dist_ema50 = ((last_close / ema50) - 1) * 100 if pd.notna(ema50) and ema50 != 0 else np.nan
            dist_52w_high = ((last_close / high_52w) - 1) * 100 if pd.notna(high_52w) and high_52w != 0 else np.nan
            dist_52w_low = ((last_close / low_52w) - 1) * 100 if pd.notna(low_52w) and low_52w != 0 else np.nan

            if pd.notna(sma9) and pd.notna(sma20) and pd.notna(sma50):
                if last_close > sma9 > sma20 > sma50:
                    trend = "Alcista fuerte"
                elif last_close > sma20 and last_close > sma50:
                    trend = "Alcista"
                elif last_close < sma20 and last_close < sma50:
                    trend = "Bajista"
                else:
                    trend = "Mixta"
            else:
                trend = "Parcial"

            rows.append(
                {
                    "Ticker_IOL": ticker_iol,
                    "Ticker_Finviz": ticker_finviz,
                    "Close_USD": last_close,
                    "SMA_9": sma9,
                    "SMA_20": sma20,
                    "SMA_50": sma50,
                    "SMA_200": sma200,
                    "EMA_20": ema20,
                    "EMA_50": ema50,
                    "Dist_SMA20_%": dist_sma20,
                    "Dist_SMA50_%": dist_sma50,
                    "Dist_SMA200_%": dist_sma200,
                    "Dist_EMA20_%": dist_ema20,
                    "Dist_EMA50_%": dist_ema50,
                    "Avg_Volume_20d": avg_volume_20d,
                    "Relative_Volume": relative_volume,
                    "Return_1d_%": return_1d,
                    "Return_intraday_%": return_intraday,
                    "ADX_14": adx14,
                    "DI_plus_14": di_plus14,
                    "DI_minus_14": di_minus14,
                    "RSI_14": rsi14,
                    "Momentum_20d_%": momentum_20d,
                    "Momentum_60d_%": momentum_60d,
                    "Vol_20d_Anual_%": vol20,
                    "Max_3m": max_3m,
                    "Min_3m": min_3m,
                    "High_52w": high_52w,
                    "Low_52w": low_52w,
                    "Dist_52w_High_%": dist_52w_high,
                    "Dist_52w_Low_%": dist_52w_low,
                    "Drawdown_desde_Max3m_%": drawdown,
                    "Tech_Trend": trend,
                }
            )
        except Exception as exc:
            logger.warning("Technical overlay failed for %s: %s", ticker_finviz, exc)
            rows.append({"Ticker_IOL": ticker_iol, "Ticker_Finviz": ticker_finviz, "Tech_Trend": f"Error: {exc}"})

    error_count = sum(1 for row in rows if str(row.get("Tech_Trend", "")).startswith("Error"))
    logger.info(
        "Technical overlay completed: tickers=%s ok=%s errors=%s",
        len(rows),
        len(rows) - error_count,
        error_count,
    )
    return normalize_technical_overlay(pd.DataFrame(rows))
