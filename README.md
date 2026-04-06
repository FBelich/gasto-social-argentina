# Gasto Social Argentina · Dashboard

Dashboard web sobre gasto social de Argentina, basado en datos de **Presupuesto Abierto** del Ministerio de Economía.

## Stack

| Capa | Tecnología |
|---|---|
| Datos | Python (pandas, requests) |
| Formato intermedio | JSON estático |
| Frontend | HTML + CSS + JavaScript + ECharts |
| Hosting | GitHub Pages |
| Automatización | GitHub Actions |

## Estructura del repositorio

```
gasto-social-argentina/
├── scripts/
│   ├── config.py           # Configuración central (años, filtros, columnas)
│   ├── utils.py            # Funciones compartidas (normalización, I/O)
│   ├── download_data.py    # Descarga ZIPs de Presupuesto Abierto
│   ├── process_data.py     # Limpieza, consolidación histórica
│   ├── build_json.py       # Genera JSONs para el frontend
│   └── main.py             # Punto de entrada del pipeline completo
├── data/
│   ├── raw/                # CSVs descargados (ignorado por git)
│   └── processed/          # DataFrames consolidados (ignorado por git)
├── docs/                   # Raíz de GitHub Pages
│   ├── index.html
│   ├── assets/
│   │   ├── css/styles.css
│   │   └── js/{app.js,charts.js}
│   └── data/               # JSONs generados (trackeados en git)
├── .github/workflows/
│   └── update-data.yml     # GitHub Actions: actualización automática
├── requirements.txt
└── README.md
```

## Instalación y uso local

```bash
# 1. Clonar
git clone https://github.com/TU_USUARIO/gasto-social-argentina.git
cd gasto-social-argentina

# 2. Entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. Pipeline completo
python scripts/main.py --year-start 2015 --year-end 2024

# 5. Servir el frontend localmente
cd docs
python -m http.server 8000
# Abrir: http://localhost:8000
```

## Fuente de datos

[Presupuesto Abierto · Ministerio de Economía · Argentina](https://www.presupuestoabierto.gob.ar/sici/)

Archivo: `credito-mensual-{año}.zip` — crédito devengado mensual.

## Secciones disponibles

- [x] **ANSES** — Administración Nacional de la Seguridad Social
- [ ] Educación *(próximamente)*
- [ ] Salud *(próximamente)*
- [ ] Asistencia social *(próximamente)*

## Licencia

MIT — datos del Estado Nacional Argentino (dominio público).
