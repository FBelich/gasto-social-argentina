# -*- coding: utf-8 -*-
"""
main.py
=======
Punto de entrada del pipeline completo.
Corre en orden: descarga → procesamiento → generación de JSONs.

Uso:
    python scripts/main.py                   # pipeline completo
    python scripts/main.py --skip-download   # solo procesa y genera JSON
    python scripts/main.py --only-json       # solo regenera JSON (sin descargar ni procesar)
    python scripts/main.py --force           # fuerza re-descarga de todos los años
"""

import argparse
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import YEAR_START, YEAR_END

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo: Presupuesto Abierto → JSON para dashboard"
    )
    parser.add_argument("--skip-download", action="store_true",
                        help="Saltar la descarga (usar datos ya descargados)")
    parser.add_argument("--only-json", action="store_true",
                        help="Solo regenerar los JSON (saltar descarga y procesamiento)")
    parser.add_argument("--force", action="store_true",
                        help="Forzar re-descarga de todos los años")
    parser.add_argument("--year-start", type=int, default=YEAR_START)
    parser.add_argument("--year-end",   type=int, default=YEAR_END)
    args = parser.parse_args()

    inicio = datetime.now()
    logger.info("=" * 60)
    logger.info(f"  PIPELINE GASTO SOCIAL ARGENTINA")
    logger.info(f"  Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Período: {args.year_start}–{args.year_end}")
    logger.info("=" * 60)

    # ── PASO 1: Descarga ──────────────────────────────────────────────────────
    if not args.only_json and not args.skip_download:
        logger.info("\n[PASO 1/3] Descargando datos...")
        from download_data import main as download_main
        download_main(args.year_start, args.year_end, force=args.force)
    else:
        logger.info("[PASO 1/3] Descarga salteada.")

    # ── PASO 2: Procesamiento ─────────────────────────────────────────────────
    if not args.only_json:
        logger.info("\n[PASO 2/3] Procesando y consolidando datos...")
        from process_data import main as process_main
        process_main(args.year_start, args.year_end)
    else:
        logger.info("[PASO 2/3] Procesamiento salteado.")

    # ── PASO 3: Generación de JSON ────────────────────────────────────────────
    logger.info("\n[PASO 3/3] Generando JSONs para el frontend...")
    from build_json import main as build_main
    build_main()

    fin = datetime.now()
    duracion = (fin - inicio).seconds
    logger.info("\n" + "=" * 60)
    logger.info(f"  Pipeline completo en {duracion}s.")
    logger.info(f"  Archivos JSON listos en: docs/data/")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
