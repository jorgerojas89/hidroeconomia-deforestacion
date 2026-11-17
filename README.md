# ¿Cuánto vale el bosque para una hidroeléctrica? — versión 2.0

**El efecto de la deforestación en la generación de energía hidroeléctrica: evidencias en el territorio colombiano**
Jorge Enrique Rojas Sánchez · Tesis de Maestría en Economía, Universidad del Rosario (2019) · versión 2.0 en curso (2026)

🗺️ **Visor interactivo:** https://jorgerojas89.github.io/hidroeconomia-deforestacion/
📦 **Versión publicada en 2019:** etiqueta [`v2019`](https://github.com/jorgerojas89/hidroeconomia-deforestacion/tree/v2019) y carpeta [`legacy_2019/`](legacy_2019/)

> **Estado:** en construcción, rama `tesis-2.0`. El código todavía no produce resultados. Los resultados de 2019 siguen siendo los publicados hasta que esta versión se termine.

*English summary below.*

---

## Qué es esta versión

La tesis de 2019 estimó que la deforestación de la cuenca reduce la generación de las centrales a filo de agua y no la de las centrales con embalse. Esta versión vuelve a construir la base desde fuentes públicas, con código que cualquiera puede ejecutar de principio a fin, y vuelve a estimar.

La pregunta, la hipótesis y el diseño central no cambian. Cambian los datos y la estimación:

| Elemento | 2019 | 2.0 |
|---|---|---|
| Periodo | 2001–2015 | 2001–2015 (réplica) y 2001–2024 |
| Deforestación | Flujo anual, grilla de 208 m | Flujo y acumulado desde 2000, a 30 m (Hansen GFC v1.12) |
| Lluvia | Interpolación de estaciones IDEAM | CHIRPS v3, promedio de cuenca |
| Cuencas | Delimitación propia con DEM | Delimitación oficial del IGAC donde existe; DEM para las demás |
| Capacidad | Fija | Capacidad efectiva neta de XM, por año |
| Efectos fijos | Planta | Planta y año |
| Errores estándar | Sin agrupar | Agrupados por sistema hídrico |

La especificación principal y las pruebas de robustez quedaron fijadas antes de estimar. Están en [`PLAN.md`](PLAN.md), sección 4.5.

## Estructura

```
├── README.md
├── PLAN.md                      # plan de trabajo y especificación fijada
├── data/
│   ├── raw/                     # descargas sin tocar (no se versionan)
│   ├── interim/                 # tablas intermedias (no se versionan)
│   └── processed/               # panel final y diccionario de datos
├── code/
│   ├── 00_tabla_maestra/        # una fila por central, llave = código de recurso XM
│   ├── 01_cuencas/              # polígonos oficiales (IGAC) y propios (DEM)
│   ├── 02_deforestacion/        # Earth Engine: Hansen por cuenca y año
│   ├── 03_lluvia/               # Earth Engine: CHIRPS por cuenca y mes
│   ├── 04_xm/                   # pydataxm: generación, capacidad, aportes, volumen útil
│   ├── 05_panel/                # unión, pruebas de calidad, comparación con 2019
│   ├── 06_estimacion/           # R + fixest
│   └── 07_figuras_tablas/
├── output/
│   ├── tablas/
│   └── figuras/
├── docs/                        # visor web (GitHub Pages)
└── legacy_2019/                 # scripts, datos y README de 2019, sin cambios
```

## Cómo correrlo

Se completa a medida que avance cada etapa. Herramientas previstas:

- **Python 3.11+** para descargas: `pydataxm` (XM) y `earthengine-api` (Hansen y CHIRPS).
- **R 4.3+** para estimar: `fixest`, `sf`, `data.table`.
- Una cuenta de Google Earth Engine registrada para uso no comercial.

Los datos crudos no están en el repositorio. Cada carpeta de `code/` trae el script que los descarga o los calcula. Ver [`data/README.md`](data/README.md).

## Cómo citar

> Rojas Sánchez, J. E. (2019). *El efecto de la deforestación en la generación de energía hidroeléctrica: evidencias en el territorio colombiano*. Tesis de Maestría en Economía, Universidad del Rosario, Bogotá.

La cita de la versión 2.0 se agregará cuando se publique.

---

## English summary

**How much is a forest worth to a hydropower plant? — version 2.0.** This branch rebuilds the 2019 MSc thesis (Universidad del Rosario) from public data with fully reproducible code. It keeps the original question — does catchment deforestation reduce output at run-of-river plants but not at reservoir plants? — and re-estimates it with 30 m Hansen forest loss (flow and cumulative), CHIRPS rainfall, official IGAC catchments where available, time-varying net effective capacity from XM, plant and year fixed effects, and clustered standard errors. The main specification was registered before estimation (see `PLAN.md`, section 4.5). The 2019 version is preserved under the `v2019` tag and in `legacy_2019/`.

Code: MIT License. Data belong to their original sources (XM, IGAC, IDEAM, UPME, Hansen et al., CHC/UCSB).
