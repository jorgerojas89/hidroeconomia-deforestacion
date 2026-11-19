# T6 — Panel (Tesis 2.0)

Une T2 (tabla maestra), T3 (cuencas IGAC), T4 (Earth Engine) y T5 (XM) en el panel 2001–2024. **No estima nada**: sin correlaciones ni regresiones entre deforestación y generación (eso es T7, con la especificación fijada en la sección 4.5 del plan).

## Cómo correr

Desde `03_tesis`, en este orden:

```
python3 -m pip install pandas pyarrow openpyxl   # pyarrow para Parquet; openpyxl para DF.xlsx
python3 03_codigo/04_panel/construir_panel.py
python3 03_codigo/04_panel/anexo_comparacion_2019.py
```

Si falta `pyarrow`, el script escribe solo los CSV y lo avisa.

## Salidas (`02_datos/panel/`)

| Archivo | Contenido |
|---|---|
| `panel_anual.csv` / `.parquet` | 2.184 filas: las 91 unidades de la tabla maestra × 2001–2024; `muestra_principal` marca las 26 |
| `panel_mensual.csv` / `.parquet` | 26.208 filas: 91 unidades × 288 meses (prueba de época seca, 4.3.3) |
| `diccionario_datos.csv` / `.md` | cada variable: definición, unidad, fuente, archivo de origen, panel |
| `reporte_qc_t6.md` | pruebas automáticas y conteo de observaciones por especificación |
| `conteo_observaciones.csv` | el mismo conteo en tabla |
| `anexo_comparacion_2019.csv` / `.md` | 19 centrales comunes con 2019: áreas, tipo, generación, FC, deforestación, lluvia (2001–2015) |

## Variables clave para T7

- Dependiente: `fc` (horas del año completo, 4.5). `fc_horas_operacion` solo para la robustez con años parciales.
- Deforestación: medida A `def_acum_pct`; medida B `def_flujo_pct` (y `def_flujo_ha`). Rezagos `_l1`–`_l3`; adelantos (placebo) `_f1`–`_f3`. El acumulado rezagado vale 0 antes de 2001 por definición; el flujo rezagado queda vacío.
- Lluvia: `lluvia_mm`, `lluvia_anom_pct`. Tipo: `embalse` (incluye embalse por cadena). Agrupación: `sistema_geom_A` (principal), `sistema_geom_B`.
- Muestra de estimación: `obs_principal == 1` (anual) y `obs_principal_mes == 1` (mensual).
- Control en todas las especificaciones: `miel_trasvase_guarino`, `miel_trasvase_manso` (0 fuera de Miel I).
- Época seca: `seca_principal` (= `seca_cuenca_4m`); robustez `seca_nal_dic_mar`.
- Caudales (4.3.6): `cv_diario` principal, `q7min_rel` segunda; filtrar `usar_prueba_mecanismo == 1` y `q_anio_completo == 1`.
- Secundarias: `regulacion_dias` (regulación continua), `oni`, `precio_bolsa_cop2024_kwh` (sale del modelo por los efectos fijos de año; sirve para valorar).

## Marcas de robustez

`fc_mayor_1`, `mes_sin_registro` / `n_meses_sin_registro`, `anio_nino`, `antes_inicio_xm`, `entrada_real_anterior`, `anio_parcial`, `mes_entrada`, `despues_fin`, `hueco_caudal_chinchina`, `miel_trasvase_guarino`, `miel_trasvase_manso`, `sonson_sin_generar`, `gen_anual_desde_mensual`.

## Decisiones de T6 (18-nov-2026, sin ver resultados)

Están en el diccionario `DECISIONES` al inicio de `construir_panel.py` y en el registro de cambios de la sección 4.5 del plan:

1. Época seca: principal = 4 meses más secos de cada cuenca (climatología CHIRPS 2001–2024); robustez = diciembre–marzo.
2. Miel I: ATCH completa todo el periodo y control de trasvase activo (Guarinó, Manso) en todas las especificaciones; robustez sin Miel I 2001–2013.
3. Años de operación parcial: fuera de la estimación principal (14 unidad-año); robustez con FC sobre horas de operación.
4. Caudales 4.3.6: `cv_diario` principal y `q7min_rel` segunda.

Además, sin decisión nueva: Caracolí 2021–2022 (XM sin ningún registro) entra con generación 0 por la regla T5-4, marcado; Sonsón 2023–2024 queda vacío (fuera de operación).

## Cuando cambie la muestra

Volver a correr T2 → T3 → T4 → T5 y luego estos dos scripts. El panel toma la marca de muestra y los sistemas de los archivos de T2 y T3.
