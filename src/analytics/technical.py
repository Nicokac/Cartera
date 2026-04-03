from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from ..clients.market_data import fetch_price_history
except ImportError:
    from clients.market_data import fetch_price_history


def normalize_technical_overlay(df_tech: pd.DataFrame) -> pd.DataFrame:
    if df_tech is None:
        return pd.DataFrame()
    return df_tech.copy()


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
) -> pd.DataFrame:
    if df_cedears is None or df_cedears.empty:
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

            last_close = float(close.iloc[-1])
            sma9 = float(close.rolling(9).mean().iloc[-1]) if len(close) >= 9 else np.nan
            sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else np.nan
            sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else np.nan
            ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1]) if len(close) >= 20 else np.nan
            ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1]) if len(close) >= 50 else np.nan
            rsi14 = float(compute_rsi(close, 14).iloc[-1]) if len(close) >= 20 else np.nan
            returns = close.pct_change().dropna()
            vol20 = float(returns.tail(20).std() * np.sqrt(252) * 100) if len(returns) >= 20 else np.nan
            momentum_20d = float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) >= 21 else np.nan
            momentum_60d = float((close.iloc[-1] / close.iloc[-61] - 1) * 100) if len(close) >= 61 else np.nan
            max_3m = float(close.tail(63).max()) if len(close) >= 20 else np.nan
            min_3m = float(close.tail(63).min()) if len(close) >= 20 else np.nan
            drawdown = float((last_close / max_3m - 1) * 100) if pd.notna(max_3m) and max_3m != 0 else np.nan
            dist_sma20 = ((last_close / sma20) - 1) * 100 if pd.notna(sma20) and sma20 != 0 else np.nan
            dist_sma50 = ((last_close / sma50) - 1) * 100 if pd.notna(sma50) and sma50 != 0 else np.nan
            dist_ema20 = ((last_close / ema20) - 1) * 100 if pd.notna(ema20) and ema20 != 0 else np.nan
            dist_ema50 = ((last_close / ema50) - 1) * 100 if pd.notna(ema50) and ema50 != 0 else np.nan

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
                    "EMA_20": ema20,
                    "EMA_50": ema50,
                    "Dist_SMA20_%": dist_sma20,
                    "Dist_SMA50_%": dist_sma50,
                    "Dist_EMA20_%": dist_ema20,
                    "Dist_EMA50_%": dist_ema50,
                    "RSI_14": rsi14,
                    "Momentum_20d_%": momentum_20d,
                    "Momentum_60d_%": momentum_60d,
                    "Vol_20d_Anual_%": vol20,
                    "Max_3m": max_3m,
                    "Min_3m": min_3m,
                    "Drawdown_desde_Max3m_%": drawdown,
                    "Tech_Trend": trend,
                }
            )
        except Exception as exc:
            rows.append({"Ticker_IOL": ticker_iol, "Ticker_Finviz": ticker_finviz, "Tech_Trend": f"Error: {exc}"})

    return normalize_technical_overlay(pd.DataFrame(rows))
