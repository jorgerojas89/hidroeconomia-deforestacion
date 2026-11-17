# Código

Cada carpeta es una etapa. Se corren en orden; cada una lee lo que dejó la anterior.

| Etapa | Lenguaje | Lee | Escribe |
|---|---|---|---|
| `00_tabla_maestra/` | Python | XM (API, PARATEC), `legacy_2019/data/DF.xlsx`, certificados IGAC | `data/processed/tabla_maestra.csv` |
| `01_cuencas/` | R o Python | Shapes IGAC, DEM, tabla maestra | `data/processed/cuencas.gpkg` |
| `02_deforestacion/` | Earth Engine (Python o JS) | `cuencas.gpkg` | `data/interim/deforestacion_cuenca_anio.csv` |
| `03_lluvia/` | Earth Engine (Python o JS) | `cuencas.gpkg` | `data/interim/lluvia_cuenca_mes.csv` |
| `04_xm/` | Python (`pydataxm`) | Tabla maestra | `data/interim/xm_*.csv` |
| `05_panel/` | R | Todo lo anterior | `data/processed/panel.csv` y diccionario |
| `06_estimacion/` | R (`fixest`) | Panel | `output/tablas/` |
| `07_figuras_tablas/` | R | Resultados | `output/figuras/`, `output/tablas/` |

Convenciones:

- Nombres de archivo con número de orden: `01_descargar_recursos.py`, `02_cruzar_nombres.py`.
- Rutas relativas a la raíz del repositorio. Nada de rutas de un computador en particular.
- Cada script termina con pruebas de control (rangos, llaves únicas, años completos) y falla si no las pasa.
