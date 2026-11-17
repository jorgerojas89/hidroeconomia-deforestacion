# Datos

| Carpeta | Qué va | ¿Se versiona? |
|---|---|---|
| `raw/` | Descargas sin modificar, una subcarpeta por fuente | No. Se reconstruye con los scripts de `code/` |
| `interim/` | Tablas intermedias (por cuenca, por central, por mes) | No. Se regenera corriendo el flujo |
| `processed/` | Panel final, tabla maestra de centrales, cuencas y diccionario de datos | Sí, si pesan poco |

## Fuentes

| Insumo | Fuente | Script | Destino |
|---|---|---|---|
| Listado y capacidad de centrales | XM (API y PARATEC) | `code/00_tabla_maestra/` | `raw/xm/` |
| Cuencas oficiales | IGAC (certificados de delimitación, 2026; shapes vía Minambiente) | `code/01_cuencas/` | `raw/igac/` |
| Modelo de elevación | Copernicus DEM GLO-30 o MERIT Hydro | `code/01_cuencas/` | `raw/dem/` |
| Pérdida de bosque | Hansen et al., Global Forest Change v1.12 (2000–2024) | `code/02_deforestacion/` (Earth Engine) | `interim/` |
| Lluvia | CHIRPS v3, Climate Hazards Center, UCSB | `code/03_lluvia/` (Earth Engine) | `interim/` |
| Generación, capacidad efectiva neta, aportes, volumen útil, precio de bolsa | XM, `pydataxm` | `code/04_xm/` | `raw/xm/` |
| Base de 2019 | Tesis original | — | `legacy_2019/data/DF.xlsx` |

## Reglas

- Nada en `raw/` se edita a mano. Si un dato está mal, se corrige en código y se documenta.
- La llave de unión es el **código de recurso de XM**. Las centrales que XM reporta juntas (por ejemplo, GUATRON o PAJARITO) son una sola unidad.
- Los certificados del IGAC (PDF) no se publican. Cada cuenca oficial se cita por el número de radicado de su certificado.
