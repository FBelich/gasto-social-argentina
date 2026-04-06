# -*- coding: utf-8 -*-
"""
download_data.py
================
Descarga los archivos ZIP de Presupuesto Abierto (crédito mensual)
para todos los años configurados en config.py.

Características:
  - Descarga incremental: omite años ya descargados (modo --force para forzar)
  - Tolerante a años sin datos (HTTP 404 → avisa y sigue)
  - Extrae el CSV del ZIP automáticamente
  - Logging detallado
"""

import argparse
import logging
import os
import zipfile
import io
import sys

import requests

# Agrega scripts/ al path para importar config y utils
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    DATA_RAW, URL_TEMPLATE, YEAR_START, YEAR_END,
    CSV_ENCODINGS, CSV_SEPS
)
from utils import asegurar_dirs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def descargar_anio(year: int, force: bool = False) -> bool:
    """
    Descarga y extrae el archivo de crédito mensual para un año dado.
    Retorna True si fue exitoso, False si no hay datos.
    """
    dest_dir = os.path.join(DATA_RAW, str(year))
    marker   = os.path.join(dest_dir, ".ok")

    # Si ya fue descargado y no se fuerza, saltar
    if os.path.exists(marker) and not force:
        logger.info(f"  [{year}] Ya descargado. Usando caché. (--force para redownload)")
        return True

    url = URL_TEMPLATE.format(year=year)
    logger.info(f"  [{year}] Descargando: {url}")

    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code == 404:
            logger.warning(f"  [{year}] 404 - Datos no disponibles para este año.")
            return False
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"  [{year}] Error de red: {e}")
        return False

    # Extraer ZIP en memoria
    try:
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
    except zipfile.BadZipFile:
        logger.error(f"  [{year}] Archivo descargado no es un ZIP válido.")
        return False

    os.makedirs(dest_dir, exist_ok=True)

    # Buscar CSV(s) dentro del ZIP
    csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_files:
        logger.warning(f"  [{year}] ZIP no contiene archivos CSV.")
        return False

    for csv_name in csv_files:
        dest_path = os.path.join(dest_dir, os.path.basename(csv_name))
        with zf.open(csv_name) as src, open(dest_path, "wb") as dst:
            dst.write(src.read())
        logger.info(f"  [{year}] Extraído: {dest_path}")

    # Marcar como descargado exitosamente
    open(marker, "w").close()
    return True


def main(year_start: int, year_end: int, force: bool = False):
    asegurar_dirs(DATA_RAW)
    logger.info(f"=== Descarga de datos: {year_start}–{year_end} ===")

    ok_years  = []
    err_years = []

    for year in range(year_start, year_end + 1):
        success = descargar_anio(year, force=force)
        if success:
            ok_years.append(year)
        else:
            err_years.append(year)

    logger.info(f"\n=== Resumen ===")
    logger.info(f"  Años disponibles: {ok_years}")
    if err_years:
        logger.warning(f"  Años sin datos:   {err_years}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descarga datos de Presupuesto Abierto")
    parser.add_argument("--year-start", type=int, default=YEAR_START)
    parser.add_argument("--year-end",   type=int, default=YEAR_END)
    parser.add_argument("--force",      action="store_true", help="Re-descargar aunque existan")
    args = parser.parse_args()
    main(args.year_start, args.year_end, args.force)
