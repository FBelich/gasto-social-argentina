# -*- coding: utf-8 -*-
"""
utils.py
========
Funciones utilitarias compartidas por todo el pipeline.
"""

import os
import re
import unicodedata  # stdlib - no external dependency needed
import logging

import pandas as pd

logger = logging.getLogger(__name__)


# ── Normalización de texto ────────────────────────────────────────────────────

def normalizar_texto(texto: str) -> str:
    """
    Normaliza un string para comparaciones robustas:
      - Convierte a minúsculas
      - Elimina acentos y diacríticos
      - Colapsa espacios múltiples
      - Elimina caracteres no alfanuméricos (salvo espacios)
    """
    if not isinstance(texto, str):
        return ""
    # Normalizar unicode (descomponer caracteres acentuados)
    nfkd = unicodedata.normalize("NFKD", texto)
    # Eliminar diacríticos (marcas de acento, etc.)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Minúsculas
    lower = sin_acentos.lower()
    # Eliminar todo excepto letras, números y espacios
    limpio = re.sub(r"[^a-z0-9 ]", " ", lower)
    # Colapsar espacios
    return re.sub(r"\s+", " ", limpio).strip()


def match_entidad(valor: str, keywords: list) -> bool:
    """
    Retorna True si el valor normalizado contiene alguno de los keywords.
    Estrategia robusta:
      1. Normaliza acentos/mayúsculas/puntuación
      2. Intenta match exacto por substring
      3. Intenta match por tokens clave (palabras largas > 4 letras)
         para cubrir abreviaciones como "SEG. SOCIAL" → "seguridad social"
    """
    val_norm = normalizar_texto(valor)

    for kw in keywords:
        kw_norm = normalizar_texto(kw)
        if not kw_norm:
            continue

        # 1. Substring directo
        if kw_norm in val_norm:
            return True

        # 2. Match por tokens significativos (palabras >4 letras)
        #    Útil cuando la fuente tiene abreviaciones
        tokens_kw  = [t for t in kw_norm.split() if len(t) > 4]
        tokens_val = [t for t in val_norm.split() if len(t) > 4]
        if tokens_kw and len(tokens_kw) >= 2:
            # Exigir que al menos el 70% de los tokens clave aparezcan en el valor
            matches = sum(1 for t in tokens_kw if t in val_norm)
            if matches / len(tokens_kw) >= 0.70:
                return True

    return False


# ── Conversión numérica ───────────────────────────────────────────────────────

def convertir_credito(serie: pd.Series) -> pd.Series:
    """
    Convierte una serie de crédito devengado a float, tolerando:
      - Puntos de miles: 1.234.567
      - Comas decimales: 1.234,56
      - Strings con espacios o caracteres extraños
      - NaN y celdas vacías
    """
    s = serie.astype(str).str.strip()
    # Detectar si el separador decimal es coma (formato europeo/argentino)
    # Heurístico: si hay comas Y puntos, el punto es separador de miles
    tiene_coma   = s.str.contains(",", na=False).any()
    tiene_punto  = s.str.contains(r"\.", na=False).any()

    if tiene_coma and tiene_punto:
        # Formato: 1.234.567,89  →  quitar puntos, cambiar coma por punto
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    elif tiene_coma and not tiene_punto:
        # Formato: 1234567,89  →  cambiar coma por punto
        s = s.str.replace(",", ".", regex=False)
    # else: ya es formato anglosajón  1234567.89  →  no tocar

    return pd.to_numeric(s, errors="coerce").fillna(0.0)


# ── Lectura robusta de CSV ────────────────────────────────────────────────────

def leer_csv_robusto(path: str, encodings: list, seps: list) -> pd.DataFrame:
    """
    Intenta leer un CSV probando combinaciones de encoding y separador.
    Retorna el primer DataFrame que tenga más de 1 columna.
    """
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False, dtype=str)
                if df.shape[1] > 1:
                    logger.info(f"  Leído con encoding={enc}, sep={repr(sep)}")
                    return df
            except Exception:
                continue
    raise ValueError(f"No se pudo leer {path} con ninguna combinación de encoding/separador.")


# ── Limpieza de columnas ──────────────────────────────────────────────────────

def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza los nombres de columna del DataFrame:
      - Minúsculas
      - Reemplaza espacios por guiones bajos
      - Elimina caracteres especiales
    """
    df = df.copy()
    df.columns = [
        re.sub(r"\s+", "_", normalizar_texto(c)).strip("_")
        for c in df.columns
    ]
    return df


def detectar_col_entidad(df: pd.DataFrame) -> str | None:
    """
    Intenta encontrar la columna de entidad en el DataFrame,
    buscando palabras clave en los nombres de columna.
    """
    candidatos = ["entidad_desc", "entidad", "organismo_desc", "organismo", "servicio_desc"]
    cols = [c.lower() for c in df.columns]
    for cand in candidatos:
        if cand in cols:
            return df.columns[cols.index(cand)]
    # Búsqueda más flexible
    for col in df.columns:
        if "entidad" in col.lower() or "organismo" in col.lower():
            return col
    return None


def detectar_col_credito(df: pd.DataFrame, nombre_buscado: str = "credito_devengado") -> str | None:
    """
    Busca la columna de crédito devengado, tolerando variaciones menores.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    if nombre_buscado in cols_lower:
        return cols_lower[nombre_buscado]
    # Búsqueda parcial
    for col_low, col_orig in cols_lower.items():
        if "credito" in col_low and "devengado" in col_low:
            return col_orig
        if "devengado" in col_low:
            return col_orig
    return None


# ── Formateo de números ───────────────────────────────────────────────────────

def fmt_millones(valor: float) -> str:
    """Formatea un número como millones con 1 decimal."""
    return f"{valor / 1_000_000:.1f} M"


# ── Helpers de filesystem ─────────────────────────────────────────────────────

def asegurar_dirs(*dirs):
    """Crea los directorios si no existen."""
    for d in dirs:
        os.makedirs(d, exist_ok=True)
