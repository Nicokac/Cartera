from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path


def load_local_env_impl(
    path: Path,
    *,
    environ: MutableMapping[str, str],
) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue
        loaded[key] = value
        environ.setdefault(key, value)

    return loaded


def resolve_iol_credentials_impl(
    *,
    username_override: str,
    password_override: str,
    non_interactive: bool,
    load_local_env_fn: Callable[[], dict[str, str]],
    environ: Mapping[str, str],
    input_fn: Callable[[str], str],
    getpass_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> tuple[str, str]:
    load_local_env_fn()

    username = username_override.strip() or str(environ.get("IOL_USERNAME", "")).strip()
    password = password_override.strip() or str(environ.get("IOL_PASSWORD", "")).strip()

    if not username:
        if non_interactive:
            raise ValueError("Usuario IOL faltante en modo no interactivo.")
        username = input_fn("Usuario IOL: ").strip()
    else:
        print_fn("Usuario IOL: cargado desde entorno")

    if not password:
        if non_interactive:
            raise ValueError("Password IOL faltante en modo no interactivo.")
        password = getpass_fn("Password IOL: ").strip()
    else:
        print_fn("Password IOL: cargado desde entorno")

    if not username or not password:
        raise ValueError("Usuario y password son obligatorios.")

    return username, password


def prompt_yes_no_impl(
    label: str,
    *,
    default: bool,
    input_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> bool:
    suffix = " [s/N]: " if not default else " [S/n]: "
    while True:
        raw = input_fn(label + suffix).strip().lower()
        if not raw:
            return default
        if raw in {"s", "si", "sí", "y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print_fn("Respuesta invalida. Ingresa 's' o 'n'.")


def prompt_money_ars_impl(
    label: str,
    *,
    input_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> float:
    while True:
        raw = input_fn(label + " ").strip()
        if not raw:
            return 0.0
        normalized = raw.replace("$", "").replace(".", "").replace(",", ".").strip()
        try:
            amount = float(normalized)
        except ValueError:
            print_fn("Monto invalido. Ingresa un numero en ARS, por ejemplo 600000.")
            continue
        if amount < 0:
            print_fn("El monto no puede ser negativo. Ingresa 0 o un valor positivo.")
            continue
        return amount


def parse_args_impl(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera el reporte real de cartera IOL.")
    parser.add_argument("--username", default="", help="Usuario IOL. Si falta, usa entorno o prompt.")
    parser.add_argument("--password", default="", help="Password IOL. Si falta, usa entorno o prompt.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Falla si faltan credenciales o politica de fondeo en vez de pedir input por terminal.",
    )
    funding_group = parser.add_mutually_exclusive_group()
    funding_group.add_argument(
        "--use-iol-liquidity",
        dest="use_iol_liquidity",
        action="store_true",
        help="Usa liquidez actual de IOL para fondear la estrategia.",
    )
    funding_group.add_argument(
        "--no-use-iol-liquidity",
        dest="use_iol_liquidity",
        action="store_false",
        help="No usa liquidez actual de IOL para fondear la estrategia.",
    )
    parser.set_defaults(use_iol_liquidity=None)
    parser.add_argument(
        "--aporte-externo-ars",
        type=float,
        default=None,
        help="Monto nuevo a ingresar en ARS. Si falta, usa prompt salvo en modo no interactivo.",
    )
    parser.add_argument(
        "--schedule-every-minutes",
        type=int,
        default=0,
        help="Si es > 0, ejecuta corridas periodicas cada N minutos (requiere --non-interactive).",
    )
    return parser.parse_args(argv)
