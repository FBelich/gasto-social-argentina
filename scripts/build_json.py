# -*- coding: utf-8 -*-
"""
build_json.py
=============
Lee los CSV procesados por process_data.py y genera los archivos JSON
que consume el frontend (docs/data/).

JSONs generados por sección:
  - {section}_timeseries.json  →  evolución histórica anual
  - {section}_composition.json →  composición del último año disponible
  - {section}_meta.json        →  metadatos (último año, total, etc.)
"""

import json
import logging
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    DATA_PROC, DOCS_DATA, SECTIONS, COL_CREDITO,
    CLASIFICADORES_INCLUIR, MAX_CATEGORIAS_GRAFICO, MIN_CATEGORIAS
)
from utils import asegurar_dirs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

MESES_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de serialización
# ─────────────────────────────────────────────────────────────────────────────

def safe_int(v):
    """Convierte a int de Python nativo (JSON serializable)."""
    try:
        return int(round(float(v)))
    except Exception:
        return 0


def guardar_json(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"  JSON guardado: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Timeseries: evolución histórica anual
# ─────────────────────────────────────────────────────────────────────────────

def build_timeseries(df: pd.DataFrame) -> dict:
    """
    Genera la serie de tiempo anual del crédito devengado total.
    También genera una desagregación por el principal clasificador económico.
    """
    if "_anio" not in df.columns or COL_CREDITO not in df.columns:
        return {}

    # Serie total anual
    ts_total = (
        df.groupby("_anio")[COL_CREDITO]
        .sum()
        .reset_index()
        .sort_values("_anio")
    )

    anios  = [int(x) for x in ts_total["_anio"]]
    totals = [safe_int(x) for x in ts_total[COL_CREDITO]]

    # Desagregación por clasificador económico de 1 dígito (si existe)
    col_clas = None
    for c in ["clasificador_economico_1_digito_desc", "clasificador_economico_3_digitos_desc",
              "clasificador_economico_8_digitos_desc", "funcion_desc", "caracter_desc"]:
        if c in df.columns and df[c].notna().sum() > 0:
            col_clas = c
            break

    datasets = []
    if col_clas:
        # Top categorías por suma total
        top_cats = (
            df.groupby(col_clas)[COL_CREDITO].sum()
            .sort_values(ascending=False)
            .head(MAX_CATEGORIAS_GRAFICO)
            .index.tolist()
        )
        for cat in top_cats:
            sub = df[df[col_clas] == cat].groupby("_anio")[COL_CREDITO].sum().reindex(anios, fill_value=0)
            datasets.append({
                "label": str(cat),
                "data":  [safe_int(v) for v in sub.values]
            })

    return {
        "labels":   anios,
        "total":    totals,
        "datasets": datasets,
        "clasificador_usado": col_clas
    }


# ─────────────────────────────────────────────────────────────────────────────
# Composition: composición del último año disponible
# ─────────────────────────────────────────────────────────────────────────────

def resumir_categorias(df_sub: pd.DataFrame, col: str, max_cats: int) -> dict:
    """
    Para una columna de clasificación, agrupa y suma el crédito.
    Aplica "Otros" para las categorías más pequeñas.
    Retorna dict listo para JSON.
    """
    agg = (
        df_sub.groupby(col, dropna=False)[COL_CREDITO]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    agg[col] = agg[col].fillna("Sin datos").astype(str).str.strip()
    agg[col] = agg[col].replace({"": "Sin datos", "nan": "Sin datos"})

    total = agg[COL_CREDITO].sum()

    # Top N + "Otros"
    if len(agg) > max_cats:
        top  = agg.iloc[:max_cats]
        rest = agg.iloc[max_cats:]
        otros_row = pd.DataFrame([{col: "Otros", COL_CREDITO: rest[COL_CREDITO].sum()}])
        agg = pd.concat([top, otros_row], ignore_index=True)

    return {
        "labels":    agg[col].tolist(),
        "values":    [safe_int(v) for v in agg[COL_CREDITO]],
        "total":     safe_int(total),
        "columna":   col,
    }


def build_composition(df: pd.DataFrame) -> dict:
    """
    Para cada clasificador relevante, genera la composición del último año.
    """
    if "_anio" not in df.columns:
        return {}

    ultimo_anio = int(df["_anio"].max())
    df_ultimo   = df[df["_anio"] == ultimo_anio].copy()

    cards = []
    for col in CLASIFICADORES_INCLUIR:
        if col not in df_ultimo.columns:
            continue
        # Excluir columnas con todos nulos o un solo valor
        validos = df_ultimo[col].dropna()
        validos = validos[validos.astype(str).str.strip() != ""]
        n_unique = validos.nunique()
        if n_unique < MIN_CATEGORIAS:
            continue

        card = resumir_categorias(df_ultimo, col, MAX_CATEGORIAS_GRAFICO)
        # Nombre de columna amigable para mostrar en el frontend
        card["titulo"] = col.replace("_desc", "").replace("_", " ").title()
        cards.append(card)

    return {
        "anio":  ultimo_anio,
        "cards": cards
    }


# ─────────────────────────────────────────────────────────────────────────────
# Meta
# ─────────────────────────────────────────────────────────────────────────────

def build_meta(df: pd.DataFrame, section_key: str) -> dict:
    """Genera metadatos de la sección."""
    cfg  = SECTIONS[section_key]
    anio_min = int(df["_anio"].min()) if "_anio" in df.columns and not df.empty else None
    anio_max = int(df["_anio"].max()) if "_anio" in df.columns and not df.empty else None
    total    = safe_int(df[COL_CREDITO].sum()) if COL_CREDITO in df.columns else 0

    # Total último año
    total_ultimo = 0
    if anio_max and "_anio" in df.columns:
        total_ultimo = safe_int(df[df["_anio"] == anio_max][COL_CREDITO].sum())

    return {
        "seccion":       section_key,
        "label":         cfg["label"],
        "color":         cfg["color"],
        "color_light":   cfg["color_light"],
        "anio_inicio":   anio_min,
        "anio_fin":      anio_max,
        "total_historico": total,
        "total_ultimo_anio": total_ultimo,
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def build_section(section_key: str):
    """
    Genera los 3 JSON de una sección.
    """
    path_csv = os.path.join(DATA_PROC, f"{section_key}.csv.gz")
    if not os.path.exists(path_csv):
        logger.error(f"  [{section_key}] No existe {path_csv}. Ejecutá process_data.py primero.")
        return

    df = pd.read_csv(path_csv, compression="gzip", low_memory=False)
    logger.info(f"  [{section_key}] {len(df):,} filas cargadas.")

    if df.empty:
        logger.warning(f"  [{section_key}] DataFrame vacío. No se generarán JSONs.")
        return

    # Asegurar tipos
    if "_anio" in df.columns:
        df["_anio"] = pd.to_numeric(df["_anio"], errors="coerce").fillna(0).astype(int)
    if COL_CREDITO in df.columns:
        df[COL_CREDITO] = pd.to_numeric(df[COL_CREDITO], errors="coerce").fillna(0.0)

    # Generar JSONs
    ts   = build_timeseries(df)
    comp = build_composition(df)
    meta = build_meta(df, section_key)

    guardar_json(ts,   os.path.join(DOCS_DATA, f"{section_key}_timeseries.json"))
    guardar_json(comp, os.path.join(DOCS_DATA, f"{section_key}_composition.json"))
    guardar_json(meta, os.path.join(DOCS_DATA, f"{section_key}_meta.json"))

    # JSON consolidado para fácil consumo desde el frontend
    combined = {"meta": meta, "timeseries": ts, "composition": comp}
    guardar_json(combined, os.path.join(DOCS_DATA, f"{section_key}.json"))


def build_index():
    """
    Genera docs/data/index.json con el listado de secciones disponibles.
    Permite al frontend descubrir qué secciones existen.
    """
    secciones = []
    for key, cfg in SECTIONS.items():
        json_path = os.path.join(DOCS_DATA, f"{key}_meta.json")
        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                meta = json.load(f)
            secciones.append(meta)
    guardar_json({"secciones": secciones, "generado": datetime.now().isoformat()},
                 os.path.join(DOCS_DATA, "index.json"))


def main():
    asegurar_dirs(DOCS_DATA)
    logger.info("=== Generación de JSONs para el frontend ===")
    for section_key in SECTIONS:
        logger.info(f"Procesando sección: {section_key.upper()}")
        build_section(section_key)
    build_index()
    logger.info("=== JSONs generados correctamente ===")


if __name__ == "__main__":
    main()
