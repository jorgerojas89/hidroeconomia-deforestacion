# T4 — Deforestación y lluvia en Earth Engine: cómo correrlo

Tres scripts, en este orden. Los de Python se corren desde la carpeta `03_tesis`.

| Paso | Script | Dónde corre | Qué hace |
|---|---|---|---|
| 1 | `exportar_cuencas_ee.py` | Tu Mac (ya corrido el 17-nov) | Pasa la capa `atch_unidad` (34 unidades) a `02_datos/earth_engine/atch_unidad_ee.zip`, EPSG:4326 |
| 2 | `t4_hansen_chirps_merit.js` | Code Editor de Earth Engine, con tu Gmail | Hansen, CHIRPS v3 y MERIT por cuenca; exporta 4 CSV a Google Drive |
| 3 | `procesar_t4.py` | Tu Mac | Arma `deforestacion_cuenca_anio.csv`, `lluvia_cuenca_mes.csv`, `lluvia_cuenca_anio.csv`, `validacion_merit.csv` y el reporte de calidad |

Se calculan las 34 unidades con ATCH, no solo las 26 de la muestra. La marca de muestra se aplica en el panel (T6).

## Paso 2, en detalle

**a. Abrir el Code Editor.** Entra a https://code.earthengine.google.com con tu Gmail. Arriba a la derecha aparece el proyecto de Cloud (por ejemplo `ee-jorgerojas`). Si pide registrar un proyecto, elige uso no comercial / investigación.

**b. Subir las cuencas.** Pestaña **Assets** (izquierda) → **NEW** → **Shape files (.shp, .shx, .dbf, .prj, or .zip)** → elige `02_datos/earth_engine/atch_unidad_ee.zip` → nombre del asset `atch_unidad_ee` → **UPLOAD**. Mira el avance en **Tasks** (derecha); tarda 1–3 minutos. Al terminar, el asset aparece en Assets; copia su ruta (`projects/<tu-proyecto>/assets/atch_unidad_ee`). projects/linen-arch-515013-j3/assets/atch_unidad_ee

**c. Prueba con 3 cuencas.** Botón **New → File**, pega todo `t4_hansen_chirps_merit.js`. En la línea `var ASSET = ...` pega tu ruta. Deja `PRUEBA = true` y presiona **Run**. En la consola (derecha) revisa:

- Hansen: `area_ha` casi igual a `atch_ha` (Río Grande ≈ 1.578 ha, Amoyá ≈ 51.428, Guavio ≈ 135.912).
- CHIRPS: lluvias mensuales de decenas a cientos de mm; meses con días faltantes = 0.
- MERIT: `razon_upa_atch` cerca de 1.
- En el mapa: polígonos azules sobre las cuencas y pérdida de bosque en amarillo-rojo.

La consola puede tardar 1–3 minutos en la prueba. Si dice *Computation timed out*, no es error del script: pasa al punto d (las exportaciones no tienen ese límite).

**d. Correr las 34.** Cambia a `PRUEBA = false` y **Run**. En **Tasks** aparecen 4 tareas; presiona **RUN** en cada una y acepta. Pueden tardar de 10 minutos a un par de horas (Ituango tiene 3,6 millones de ha a 30 m). Puedes cerrar el navegador.

**e. Bajar los CSV.** En Google Drive, carpeta `tesis_T4`, descarga los 4 archivos a `03_tesis/02_datos/earth_engine/crudo/`.

## Paso 3

```
cd ".../03_tesis"
python3 03_codigo/02_earth_engine/procesar_t4.py
```

Imprime y guarda `reporte_qc_t4.md`. Si alguna prueba dice FALLA, el script termina con error y no hay que seguir a T6 sin revisarla.

## Decisiones técnicas (para el anexo metodológico)

- **Bosque:** `treecover2000` ≥ 30 % (Hansen GFC v1.12). La pérdida se cuenta solo en esos píxeles. Se exporta además la pérdida sin máscara, solo como robustez.
- **Resolución:** suma de áreas reales de píxel (`ee.Image.pixelArea`) en la grilla nativa de Hansen (0,00025°, ~30 m), sin remuestreo. Corrige los dos errores de 2019: celdas de 208 m y área de celda mal calculada.
- **Lluvia:** CHIRPS v3 diario (`UCSB-CHC/CHIRPS/V3/DAILY_RNL`), sumado por mes, promedio de cuenca ponderado por área en una grilla de 0,005°. Esa grilla hace que cuencas más chicas que un píxel de CHIRPS (Río Grande, Sonsón, Riofrío) reciban el promedio de los píxeles que realmente tocan. Se calcula desde 2000 para tener el rezago.
- **Validación con MERIT Hydro, sin coordenadas de captación:** dentro de cada ATCH (recortada 300 m hacia adentro) se busca el píxel con mayor área drenada (`upa`). Si la ATCH es una cuenca hidrológica, ese píxel es la salida y su área drenada debe parecerse al área de la ATCH. Razón < 0,9: trasvases o varias salidas (se espera en Miel I). Razón > 1,1: un río más grande toca el polígono o la cuenca no cierra. Se exportan las coordenadas de la salida para compararlas con las de captación de la UPME cuando estén.
