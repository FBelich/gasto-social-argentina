# -*- coding: utf-8 -*-
"""
process_data.py
===============
Lee los CSV crudos descargados, los limpia, normaliza y consolida
en un único DataFrame histórico por sección (ANSES, etc.).

Salida: archivos Parquet/CSV en data/processed/ listos para build_json.py
"""

import glob
import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    DATA_RAW, DATA_PROC, SECTIONS, COL_CREDITO,
    CLASIFICADORES_INCLUIR, COL_PERIODO, COL_ANIO,
    CSV_ENCODINGS, CSV_SEPS
)
from utils import (
    leer_csv_robusto, normalizar_columnas,
    detectar_col_entidad, detectar_col_credito,
    convertir_credito, match_entidad, asegurar_dirs
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def detectar_anio(df: pd.DataFrame, year_folder: int) -> pd.Series:
    """
    Intenta extraer el año de alguna columna del DataFrame.
    Si no encuentra nada, usa el año del nombre de la carpeta.
    """
    for col in [COL_ANIO, COL_PERIODO, "ejercicio", "anio", "año"]:
        if col in df.columns:
            try:
                anio_serie = pd.to_numeric(df[col].astype(str).str[:4], errors="coerce")
                if anio_serie.notna().any():
                    return anio_serie.fillna(year_folder).astype(int)
            except Exception:
                pass
    return pd.Series([year_folder] * len(df), dtype=int)


def detectar_mes(df: pd.DataFrame) -> pd.Series:
    """
    Extrae el mes de la columna de período si existe.
    Retorna NaN si no se puede determinar.
    """
    for col in [COL_PERIODO, "periodo", "mes"]:
        if col in df.columns:
            s = df[col].astype(str)
            # Formato YYYYMM → mes es los últimos 2 dígitos
            if s.str.match(r"^\d{6}$").any():
                return pd.to_numeric(s.str[-2:], errors="coerce")
            # Formato MM/YYYY o YYYY-MM
            if s.str.contains(r"[-/]").any():
                try:
                    parsed = pd.to_datetime(s, errors="coerce")
                    return parsed.dt.month
                except Exception:
                    pass
    return pd.Series([None] * len(df))


def leer_csv_anio(year: int) -> pd.DataFrame | None:
    """
    Lee el CSV del año dado desde data/raw/{year}/.
    Retorna None si no hay datos.
    """
    folder = os.path.join(DATA_RAW, str(year))
    if not os.path.exists(folder):
        return None

    csvs = glob.glob(os.path.join(folder, "*.csv"))
    if not csvs:
        logger.warning(f"  [{year}] Sin CSV en {folder}")
        return None

    # Si hay más de un CSV, usar el más grande (suele ser el principal)
    csv_path = max(csvs, key=os.path.getsize)

    try:
        df = leer_csv_robusto(csv_path, CSV_ENCODINGS, CSV_SEPS)
    except ValueError as e:
        logger.error(f"  [{year}] {e}")
        return None

    if df.empty:
        logger.warning(f"  [{year}] DataFrame vacío.")
        return None

    logger.info(f"  [{year}] Leído: {len(df):,} filas, {df.shape[1]} columnas")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────────────────────────────

def procesar_anio(year: int) -> pd.DataFrame | None:
    """
    Procesa un año completo:
      1. Lee CSV crudo
      2. Normaliza nombres de columnas
      3. Detecta columna de crédito y entidad
      4. Convierte crédito a numérico
      5. Agrega columnas año/mes
      6. Retorna DataFrame limpio
    """
    df_raw = leer_csv_anio(year)
    if df_raw is None:
        return None

    # Normalizar nombres de columnas
    df = normalizar_columnas(df_raw)

    # Detectar columna de crédito
    col_cred = detectar_col_credito(df, COL_CREDITO)
    if col_cred is None:
        logger.warning(f"  [{year}] No se encontró columna de crédito. Columnas: {list(df.columns)[:10]}")
        return None

    # Convertir crédito a numérico
    df[col_cred] = convertir_credito(df[col_cred])
    # Renombrar a nombre canónico
    if col_cred != COL_CREDITO:
        df = df.rename(columns={col_cred: COL_CREDITO})

    # Agregar año y mes
    df["_anio"] = detectar_anio(df, year)
    df["_mes"]  = detectar_mes(df)

    # Detectar columna de entidad
    col_ent = detectar_col_entidad(df)
    if col_ent is None:
        logger.warning(f"  [{year}] No se encontró columna de entidad. Columnas: {list(df.columns)[:10]}")
        # Continuar de todas formas; el filtro de sección fallará con 0 filas
        df["entidad_desc"] = ""
    elif col_ent != "entidad_desc":
        df = df.rename(columns={col_ent: "entidad_desc"})

    # Asegurarse de que los clasificadores de interés existan como columnas
    for col in CLASIFICADORES_INCLUIR:
        if col not in df.columns:
            df[col] = None

    return df


def filtrar_seccion(df: pd.DataFrame, section_key: str) -> pd.DataFrame:
    """
    Filtra el DataFrame para una sección (ej. 'anses')
    usando match_entidad() con normalización robusta.
    """
    cfg = SECTIONS[section_key]
    keywords = cfg["entidad_keywords"]
    mask = df["entidad_desc"].apply(lambda v: match_entidad(str(v), keywords))
    return df[mask].copy()


def construir_base_historica(year_start: int, year_end: int) -> pd.DataFrame:
    """
    Consolida todos los años disponibles en un único DataFrame histórico.
    """
    frames = []
    for year in range(year_start, year_end + 1):
        logger.info(f"Procesando año {year}...")
        df = procesar_anio(year)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        raise RuntimeError("No se encontraron datos para ningún año. Ejecutá download_data.py primero.")

    base = pd.concat(frames, ignore_index=True, sort=False)
    logger.info(f"Base histórica consolidada: {len(base):,} filas, {base.shape[1]} columnas")
    return base


def main(year_start: int, year_end: int):
    from config import YEAR_START, YEAR_END
    year_start = year_start or YEAR_START
    year_end   = year_end   or YEAR_END

    asegurar_dirs(DATA_PROC)
    logger.info(f"=== Procesamiento: {year_start}–{year_end} ===")

    # Construir base histórica completa
    base = construir_base_historica(year_start, year_end)

    # Guardar base completa (puede ser grande, usamos CSV comprimido)
    base_path = os.path.join(DATA_PROC, "base_historica.csv.gz")
    base.to_csv(base_path, index=False, compression="gzip")
    logger.info(f"Base guardada en: {base_path}")

    # Filtrar y guardar por sección
    for section_key in SECTIONS:
        logger.info(f"Filtrando sección: {section_key.upper()}...")
        df_sec = filtrar_seccion(base, section_key)
        if df_sec.empty:
            logger.warning(f"  [{section_key}] Sin datos tras el filtro. Verificar entidad_keywords.")
        else:
            logger.info(f"  [{section_key}] {len(df_sec):,} filas encontradas.")
        out_path = os.path.join(DATA_PROC, f"{section_key}.csv.gz")
        df_sec.to_csv(out_path, index=False, compression="gzip")
        logger.info(f"  [{section_key}] Guardado en: {out_path}")

    logger.info("=== Procesamiento completo ===")


if __name__ == "__main__":
    import argparse
    from config import YEAR_START, YEAR_END
    parser = argparse.ArgumentParser()
    parser.add_argument("--year-start", type=int, default=YEAR_START)
    parser.add_argument("--year-end",   type=int, default=YEAR_END)
    args = parser.parse_args()
    main(args.year_start, args.year_end)
