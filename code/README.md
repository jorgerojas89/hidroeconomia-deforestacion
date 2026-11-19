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
| `06_estimacion/` | Python (`pyfixest`) y R (`fixest`) | Panel | `output/tablas/`, `output/figuras/` |
| `07_figuras_tablas/` | R | Resultados | `output/figuras/`, `output/tablas/` |

Convenciones:

- Nombres de archivo con número de orden: `01_descargar_recursos.py`, `02_cruzar_nombres.py`.
- Rutas relativas a la raíz del repositorio. Nada de rutas de un computador en particular.
- Cada script termina con pruebas de control (rangos, llaves únicas, años completos) y falla si no las pasa.

## Estado al sellar la etiqueta `pre-estimacion` (19-nov-2026)

El código de las etapas 00 a 05 está aquí tal como se usó para construir el panel. Todavía se corre desde la carpeta de trabajo del autor (`03_tesis/`, con datos en `02_datos/`), no desde la estructura `data/` de este repositorio; adaptar las rutas es parte de la Fase 6. Cada carpeta trae su guía (`LEEME_T4.md`, `LEEME_T5.md`, `LEEME_T6.md`).

| Etapa | Scripts, en orden |
|---|---|
| `00_tabla_maestra/` | `descargar_listado_xm.py`, `descargar_capacidad_historica_xm.py`, `extraer_generacion_por_anio.py`, `extraer_generacion_todas_2020_2024.py`, `procesar_xm_local.py`, `construir_tabla_maestra.py` |
| `01_cuencas/` | `extraer_atch_igac.py`, `analizar_cuencas.py`, `mapa_sistemas.py` |
| `02_deforestacion/` | `exportar_cuencas_ee.py`, `t4_hansen_chirps_merit.js` (Code Editor de Earth Engine: deforestación, lluvia CHIRPS y validación MERIT), `procesar_t4.py` |
| `03_lluvia/` | Vacía: la lluvia se calcula en `02_deforestacion/` |
| `04_xm/` | `descargar_xm_t5.py` (API de XM con `requests`, no `pydataxm`), `procesar_t5.py` |
| `05_panel/` | `construir_panel.py`, `anexo_comparacion_2019.py` |
| `06_estimacion/` | `01_modelo_principal.py`, `02_pruebas_4_3.py`, `03_analisis_individuales.py`, `04_figuras.py` (Python, `pyfixest`); `t7_estimacion.R` (equivalente con `fixest`). Guía: `LEEME_T7.md` |
