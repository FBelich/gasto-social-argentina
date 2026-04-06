# -*- coding: utf-8 -*-
"""
config.py
=========
Configuración central del proyecto Gasto Social Argentina.
Todos los parámetros editables están aquí: URLs, años, filtros, columnas.
"""

import os

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW    = os.path.join(BASE_DIR, "data", "raw")
DATA_PROC   = os.path.join(BASE_DIR, "data", "processed")
DOCS_DATA   = os.path.join(BASE_DIR, "docs", "data")

# ── Fuente de datos ───────────────────────────────────────────────────────────
# Presupuesto Abierto - crédito mensual por año
# Patrón de URL confirmado para los archivos disponibles.
# Algunos años anteriores pueden tener URL distinta; se maneja con fallbacks.
URL_TEMPLATE = "https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/{year}/credito-mensual-{year}.zip"

# Años a descargar (1995 – presente). El pipeline ignora años sin datos.
YEAR_START = 2002   # Los datos públicos consolidados arrancan ~2002
YEAR_END   = 2024   # Ajustar al año en curso; GitHub Actions lo sobreescribe dinámicamente

# ── Columna de crédito ────────────────────────────────────────────────────────
COL_CREDITO = "credito_devengado"

# ── Secciones del dashboard ───────────────────────────────────────────────────
# Cada sección tiene: nombre visual, color, filtros de entidad, color hex
SECTIONS = {
    "anses": {
        "label":       "ANSES",
        "color":       "#007AFF",
        "color_light": "rgba(0,122,255,.12)",
        "entidad_keywords": [
            "administracion nacional de la seguridad social",
            "administracion nacional de seguridad social",
            "administración nacional de la seg. social",
        ],
    },
    # ── Futuras secciones (descomentar y completar cuando corresponda) ─────────
    # "educacion": {
    #     "label":   "Educación",
    #     "color":   "#34C759",
    #     "color_light": "rgba(52,199,89,.12)",
    #     "entidad_keywords": ["ministerio de educacion"],
    # },
    # "salud": { ... },
}

# ── Columnas de clasificación a incluir en el análisis ───────────────────────
# Estas son las columnas no-numéricas de interés analítico confirmadas en los
# archivos de Presupuesto Abierto. Se excluyen códigos/IDs y columnas técnicas.
CLASIFICADORES_INCLUIR = [
    "clasificador_economico_8_digitos_desc",
    "clasificador_economico_3_digitos_desc",
    "clasificador_economico_1_digito_desc",
    "fuente_financiamiento_desc",
    "funcion_desc",
    "caracter_desc",
    "programa_desc",
    "tipo_de_presupuesto_desc",
]

# Columnas con demasiados valores únicos (excluir de gráficos de composición)
MAX_CATEGORIAS_GRAFICO = 10   # Top N categorías; el resto se agrupa en "Otros"
MIN_CATEGORIAS         = 2    # Si hay menos de 2 categorías, no vale graficar

# ── Columna temporal ──────────────────────────────────────────────────────────
COL_PERIODO = "periodo"   # Columna que identifica el año/mes (puede variar entre años)
COL_ANIO    = "ejercicio" # Alternativa frecuente para el año

# Codificaciones a intentar al leer CSV
CSV_ENCODINGS = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]

# ── Separadores CSV a intentar ────────────────────────────────────────────────
CSV_SEPS = [",", ";", "|", "\t"]
