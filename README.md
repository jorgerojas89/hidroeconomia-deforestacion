# ¿Cuánto vale el bosque para una hidroeléctrica?

**El efecto de la deforestación en la generación de energía hidroeléctrica: evidencias en el territorio colombiano**
Tesis de Maestría en Economía · Universidad del Rosario · 2019 · Jorge Enrique Rojas Sánchez

🗺️ **Visor interactivo:** https://jorgerojas89.github.io/hidroeconomia-deforestacion/
📄 **Documento:** [enlace al repositorio institucional de la Universidad del Rosario — por completar]

*English summary below.*

---

## Pregunta

Cerca del 65 % de la electricidad de Colombia es hidráulica. ¿La pérdida de bosque en las cuencas aportantes reduce la generación de las centrales? Y si es así, ¿cuánto vale, en energía y en dinero, conservar ese bosque?

## Hallazgos principales

- En las plantas **a filo de agua** (sin regulación artificial), la deforestación de la cuenca reduce de forma significativa el factor de capacidad: alrededor de **2,5 % de pérdida de potencia**.
- El beneficio de conservar equivale a cerca de **$3 millones COP por hectárea al año**.
- En las plantas **con embalse**, el efecto no es significativo en el periodo 2000–2015. El beneficio del bosque llega por la vía de la sedimentación (colmatación del embalse y desgaste de las turbinas), que actúa en horizontes más largos. Por eso los resultados son una **cota inferior** del valor del bosque.
- El bosque no produce *más* agua: produce agua de mejor calidad y mejor distribuida en el tiempo.

## Método

| Componente | Detalle |
|---|---|
| Unidad de análisis | Panel de 60 centrales hidroeléctricas del SIN, 2000–2015 |
| Variable dependiente | Factor de capacidad (generación / capacidad instalada) |
| Estimación | Efectos fijos de planta y de tiempo; errores agrupados por cuenca; interacción deforestación × tipo de planta (filo de agua / embalse); splines (nudos de Harrell) para no linealidades |
| Cuencas | Delimitadas a partir de un DEM con SAGA GIS desde R (`code/01_delimitacion_cuencas.R`) |
| Deforestación | Hansen et al., *Global Forest Change* |
| Generación, precios y capacidad | XM |
| Precipitación | IDEAM (interpolación spline) |
| Ubicación de plantas | UPME / IGAC |

## Contenido del repositorio

```
├── code/
│   ├── 01_delimitacion_cuencas.R   # delimitación de cuencas, versión ordenada
│   └── original_2019/              # scripts tal como se usaron en 2019 (ver LEEME)
├── data/
│   ├── xm/                         # generación, volumen útil, caudales, precio de bolsa, capacidad
│   ├── upme/                       # tablas de centrales hidráulicas
│   └── README.md                   # fuentes y cómo descargar los datos que no están aquí
└── docs/                           # visor web (GitHub Pages)
```

## Limitaciones de esta versión

- Los scripts de 2019 usan `rgdal`, `maptools` y `rgeos`, retirados de CRAN en 2023. La versión ordenada los reemplaza por `sf`, pero **no se ha vuelto a ejecutar** con los datos originales.
- Este repositorio todavía no incluye los scripts de estimación econométrica ni la base de panel final. Se agregarán en una próxima versión.
- El DEM, los drenajes del IGAC, la precipitación del IDEAM y las capas de deforestación no se suben por su tamaño. Ver `data/README.md`.

## Cómo citar

> Rojas Sánchez, J. E. (2019). *El efecto de la deforestación en la generación de energía hidroeléctrica: evidencias en el territorio colombiano*. Tesis de Maestría en Economía, Universidad del Rosario, Bogotá.

---

## English summary

**How much is a forest worth to a hydropower plant?** Using a 2000–2015 panel of 60 Colombian hydropower plants, catchments delineated from a DEM, and Global Forest Change deforestation data, this MSc Economics thesis (Universidad del Rosario, 2019) estimates the effect of catchment deforestation on plant capacity factors with fixed-effects and spline models. For run-of-river plants, deforestation reduces output by about 2.5%, implying a conservation benefit of roughly COP 3 million per hectare per year. For reservoir plants the effect works through siltation over longer horizons, so the estimates are a lower bound.

Code: MIT License. Data belong to their original sources (XM, UPME, IDEAM, IGAC, Hansen et al.).
