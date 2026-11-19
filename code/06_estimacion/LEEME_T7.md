# T7 · Estimación

Especificación fijada en la sección 4.5 del plan (etiqueta `pre-estimacion`, commit `b9a6f68`) y su registro de cambios. Se estima con `pyfixest` (Python); `t7_estimacion.R` hace lo mismo con `fixest` para replicar en el Mac (registro de cambios, 19-nov-2026).

## Cómo correr

Desde `03_tesis/`, en este orden:

```bash
python3 -m pip install pyfixest pyarrow statsmodels matplotlib
python3 03_codigo/05_estimacion/01_modelo_principal.py      # conteo + modelo principal + criterio de 4.5
python3 03_codigo/05_estimacion/02_pruebas_4_3.py           # pruebas 2–8 de 4.3 (la 7 queda pendiente)
python3 03_codigo/05_estimacion/03_analisis_individuales.py # 4.3.9: por unidad, influencia, errores alternativos
python3 03_codigo/05_estimacion/04_figuras.py               # figuras
Rscript 03_codigo/05_estimacion/t7_estimacion.R             # equivalente en R; compara con las tablas de Python
```

Tarda menos de un minuto en total. Lee `02_datos/panel/panel_anual` y `panel_mensual` (Parquet; si OneDrive lo tiene solo en la nube, usa el CSV gemelo). Escribe en `07_salidas/tablas/` (CSV y Markdown) y `07_salidas/figuras/`.

## Qué estima

Modelo principal, una regresión por medida de deforestación (acumulado %, flujo en miles de ha, flujo %):

```
FC_it (pp) = b1·D_it + b2·D_it×Embalse_i + b3·Lluvia_it (miles de mm) + c1·TrasvGuarino_it + c2·TrasvManso_it + mu_i + lambda_t + e_it
```

- Muestra `obs_principal == 1`: 524 unidad-año, 26 unidades, 10 sistemas A. `01` falla si los conteos no coinciden con `conteo_observaciones.csv` de T6.
- Errores agrupados por `sistema_geom_A`. p convencional: CRV1 de `pyfixest`, t con G − 1 gl. p bootstrap: *wild cluster restricted bootstrap* (impone la nula), pesos de Webb, 9.999 réplicas, semilla 20261119.
- El bootstrap está programado en `t7_comun.py` (algoritmo de Roodman, MacKinnon, Nielsen y Webb 2019, el de `boottest`/`fwildclusterboot`) porque `wildboottest` 0.3.2 falla con identificadores de grupo de texto. Se validó contra `wildboottest` con una variable simulada (p 0,022 frente a 0,024; 0,213 frente a 0,211; 0,291 frente a 0,296). Los efectos fijos entran como indicadoras, y el script comprueba que reproducen los coeficientes de `pyfixest`.
- b1 + b2 = 0 es una sola restricción: F = t².

Definiciones de las pruebas (fijadas en el código antes de correr la primera regresión): ver el encabezado de `02_pruebas_4_3.py` y `03_analisis_individuales.py`.

## Tablas

| Archivo | Contenido |
|---|---|
| `t7_00_conteo_observaciones` | Observaciones por muestra y esperadas de T6 |
| `t7_01_modelo_principal` | b1, b2, b1 + b2, lluvia, trasvases; las tres medidas |
| `t7_01_criterio_4_5` | Cada medida frente al criterio de 4.5, con p convencional y bootstrap |
| `t7_02_2_rezagos` … `t7_02_8_muestra` | Pruebas 2 a 8 de 4.3 (`t7_02_7_smbyc`: pendiente) |
| `t7_02_resumen_pruebas` | Todas las pruebas en una tabla |
| `t7_03_por_unidad`, `_resumen` | Regresión por unidad (Newey-West 2 rezagos) y resumen por tipo |
| `t7_03_influencia` | Quitar una unidad o un sistema a la vez |
| `t7_03_errores_alternativos` | Errores por unidad (26) y por sistema B (14) |
| `t7_resumen.md` | Resumen de una página |

## Notas de muestra (registro de cambios, 19-nov, después de ver resultados)

- **Caudales:** `cv_diario` y `q7min_rel` necesitan la serie diaria de XM; existen en 218 de las 349 unidad-año del conteo de T6 (216 tras quitar celdas de una sola observación), 8 sistemas.
- **Mensual:** `pyfixest` retira observaciones que quedan solas en su celda año × mes (34 en la época seca propia). No cambian los coeficientes; `fixest` en R las conserva, así que el N puede diferir.
