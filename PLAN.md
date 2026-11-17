# Plan para volver a correr la tesis

**El efecto de la deforestación en la generación de energía hidroeléctrica: evidencias en el territorio colombiano**
Jorge Enrique Rojas Sánchez · plan elaborado el 16 de noviembre de 2026 · decisiones registradas el 17 de noviembre de 2026

> Las rutas que empiezan por `03_tesis/` son de la carpeta de trabajo del autor, no de este repositorio.

---

## 1. Decisión de fondo

No conviene reparar la base de 2019. Conviene reconstruirla desde fuentes públicas, con código que cualquiera pueda volver a ejecutar, y estimar de nuevo.

Razones:

- El script que produjo las tablas publicadas no aparece. Hoy la tesis no es replicable ni por su autor.
- La base tiene errores confirmados (sección 2) que afectan los coeficientes.
- Todos los insumos tienen hoy una versión pública mejor que la de 2019, y casi todos llegan hasta 2024. El panel puede pasar de 15 a 24 años.
- Para un artículo, un revisor va a pedir exactamente lo que faltó: efectos fijos de año, errores agrupados, deforestación acumulada y evidencia del mecanismo.

La pregunta, la hipótesis y el diseño central no cambian: ¿la deforestación de la cuenca reduce la generación de las centrales a filo de agua y no la de las centrales con embalse?

---

## 2. Qué falló en 2019 y cómo se evita

| Problema encontrado | Evidencia | Cómo se evita ahora |
|---|---|---|
| Lluvia inválida en 2011, 2012 y 2013 | Todas las cuencas valen entre 11 y 12 esos años, frente a 740–5.790 mm en los demás. Las 788 observaciones de las tablas indican que esos años sí entraron a la regresión | Lluvia satelital (CHIRPS) para toda la serie, con una prueba automática de rangos por año |
| No hay script de estimación | El R disponible solo tiene modelos exploratorios en logaritmos; splines y kernel no están | Un solo flujo de código versionado, de datos crudos a tablas |
| Efectos fijos de año declarados pero no estimados | Las tablas reportan coeficiente para el precio de bolsa, que solo varía por año | Efectos fijos de planta y de año; el precio sale del modelo |
| Sin errores agrupados | Las tablas no los reportan | Agrupar por cuenca o sistema hídrico |
| Deforestación medida en grilla de 208 m | 4,34 ha por celda, en vez de los 30 m originales | Conteo a resolución nativa, dentro de la máscara de bosque del año 2000 |
| Factores de capacidad mayores que 1 | Máximo de 1,32; capacidad mal declarada (Río Grande) | Capacidad efectiva neta de XM, variable en el tiempo |
| Cuencas mal delimitadas | San Carlos (1.240 MW) con 178 ha; Jaguas con 3.394 ha | Delimitación oficial del IGAC donde exista; validación de áreas |
| Emparejamiento de nombres | Alto y Bajo Anchicayá sin generación; "Albán" sin cuenca | Tabla maestra de centrales con el código de recurso de XM como llave |
| Muestra y tipos inconsistentes | 36 centrales de filo en la Tabla 2, 24 en la Tabla 6; hoja de tipos de una muestra anterior de 55 | Tipo de central tomado de una fuente única y documentado por planta |

---

## 3. Datos públicos disponibles

### 3.1 Verificados

| Insumo | Fuente | Cobertura | Acceso | Notas para la tesis |
|---|---|---|---|---|
| Pérdida de bosque | Hansen et al., Global Forest Change v1.12 | 2000–2024, 30 m | [Descarga por teselas](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html) · [Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12) | Capas `lossyear` y `treecover2000`. El algoritmo cambió hacia 2011; la serie no es del todo homogénea antes y después. Los efectos fijos de año absorben el salto común |
| Lluvia | CHIRPS v3 (UC Santa Barbara) | 1981–presente, 0,05° (≈5,5 km), diaria y mensual | [Portal CHC](https://www.chc.ucsb.edu/data) · [Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHC_CHIRPS_V3_DAILY_RNL) | Reemplaza la interpolación de estaciones. Permite separar época seca y de lluvias |
| Lluvia de estaciones | IDEAM, DHIME | Histórico por estación | [DHIME](http://dhime.ideam.gov.co/atencionciudadano/) · [Precipitación nacional diaria (zip)](http://bart.ideam.gov.co/PQRS/AQTSUtils/PrecipitacionNacionalDiaria.zip) | Para validar CHIRPS en algunas cuencas, no como fuente principal |
| Generación, precio de bolsa, capacidad efectiva neta, aportes, volumen útil | XM | Desde 2000 | [API XM y pydataxm](https://github.com/EquipoAnaliticaXM/API_XM) · SiMEM (datos abiertos, CSV/JSON/XML y API) · Sinergox | Generación por recurso horaria. 2000–2018 ya descargado (ver `legacy_2019/data/xm`) |
| Listado y capacidad de plantas en operación | XM, PARATEC | Vigente | [PARATEC generación](https://paratec.xm.com.co/paratec/SitePages/generacion.aspx?q=capacidad) | Para la tabla maestra: nombre oficial, capacidad, tipo, fecha de entrada |
| Deforestación oficial | IDEAM, SMByC | Anual solo desde 2013; antes, periodos irregulares (2000–2005, 2005–2010, 2010–2012) | [SMByC](http://smbyc.ideam.gov.co/) | No sirve para el panel anual completo. Sí como robustez 2013–2024 y para las cifras de contexto |
| Embalses y cartografía básica | IGAC, datos abiertos | Nacional | [Hub de datos abiertos IGAC](https://datos-abiertos-igac-igac-oit.hub.arcgis.com/) · [Capa Embalse en datos.gov.co](https://www.datos.gov.co/dataset/Embalse/igd9-6s52) | Licencia CC BY 4.0. Sirve para confirmar qué centrales tienen embalse |

### 3.2 Cuencas oficiales del IGAC

La norma de transferencias del sector eléctrico asigna al IGAC la delimitación de las áreas de cuenca y embalse de cada central.

**Estado al 17 de noviembre de 2026:**

- Hay **37 certificados de delimitación del IGAC (2026)** en `03_tesis/02_datos/IGAC_certificados`, con su código de recurso XM ya cruzado en `precarga_proyectos.csv`.
- Los **shapes** se piden a través del Minambiente. No se hará PQRSD al IGAC.
- En el artículo, cada cuenca oficial se cita por el número de radicado de su certificado. Así un tercero sabe qué documento pedir.

Precauciones:

- **Cubren solo centrales de más de 10 MW**, las obligadas a transferir. La mayoría de las centrales a filo de agua de la muestra están por debajo de ese umbral.
- **Definen la cuenca para efectos fiscales**, no necesariamente la cuenca aportante hidrológica hasta la captación. Hay que comparar ambas.
- Algunas centrales están agrupadas en XM (Guadalupe III + IV + Troneras = GUATRON; Pajarito I + II = PAJARITO). En el panel se tratan como una sola unidad, porque XM reporta la generación conjunta.

Qué hacer con ella:

1. Usarla como delimitación principal para las centrales que tengan certificado.
2. Delimitar con modelo de elevación las demás, con los scripts de cuencas corregidos.
3. Validar el método propio contra la oficial en las centrales donde existan las dos. Si coinciden, eso respalda las cuencas de las centrales pequeñas.

### 3.3 Fuentes por verificar

Confirmar disponibilidad antes de depender de ellas.

| Insumo | Fuente probable | Uso |
|---|---|---|
| Modelo de elevación | Copernicus DEM GLO-30, SRTM, MERIT Hydro | Delimitar cuencas de centrales pequeñas |
| Cuencas de referencia | HydroBASINS; zonificación hidrográfica del IDEAM | Validación y agrupación por sistema hídrico |
| Fenómeno de El Niño | Índice ONI de NOAA | Control y pruebas de robustez |
| Índice de precios | DANE o Banco de la República | Llevar la valoración a pesos constantes actuales |
| Ubicación y atributos de centrales | UPME (SIMEC) | Coordenadas de captación |
| Costos de oportunidad | CONPES 3886 y sus fuentes (DANE, Agronet) | Comparación con el valor por hectárea |

---

## 4. Diseño nuevo del estudio

### 4.1 Lo que cambia

| Elemento | Tesis 2019 | Versión nueva |
|---|---|---|
| Periodo | 2001–2015 | 2001–2015 (réplica) y luego 2001–2024 |
| Frecuencia | Anual | Anual y mensual (para separar época seca) |
| Deforestación | Flujo anual, grilla de 208 m | Flujo anual y acumulado desde 2000, a 30 m, sobre el bosque existente en 2000 |
| Lluvia | Interpolación de estaciones | CHIRPS promedio de cuenca; anual, de época seca y anomalía |
| Capacidad | Fija, de varias fuentes | Capacidad efectiva neta de XM, variable en el tiempo |
| Tipo de central | Indicadora filo / embalse | Indicadora, más una medida continua de regulación (volumen útil sobre aporte medio) |
| Efectos fijos | Planta | Planta y año |
| Errores | Sin agrupar | Agrupados por cuenca o sistema hídrico |
| Precio de bolsa | Control | Sale del modelo; lo absorben los efectos fijos de año |

### 4.2 Especificación principal

```
FC_it = b1·D_it + b2·(D_it × Embalse_i) + b3·Lluvia_it + mu_i + lambda_t + e_it
```

- `FC`: factor de capacidad. `D`: deforestación de la cuenca. `mu_i`: efecto fijo de planta. `lambda_t`: efecto fijo de año.
- Hipótesis: `b1 < 0` y `b2 > 0`, con `b1 + b2` cercano a cero.

### 4.3 Pruebas que dan credibilidad

1. **Acumulado frente a flujo.** Estimar con la fracción de cuenca deforestada desde 2000. Responde si la pérdida persiste.
2. **Rezagos.** Deforestación de uno a tres años atrás. Una hectárea deforestada no se recupera al año siguiente.
3. **Época seca.** El mecanismo predice que el efecto se concentra en los meses secos. Es la prueba más directa de la regulación hídrica.
4. **Placebo temporal.** La deforestación futura no debe explicar la generación presente. Si la explica, hay un factor omitido.
5. **Sin años de El Niño.** Excluir 2009–2010, 2015–2016 y 2023–2024 y ver si el resultado se sostiene.
6. **Caudales.** Con los aportes de XM, medir si la variabilidad del caudal aumenta con la deforestación. Es observar el mecanismo en vez de inferirlo.
7. **Fuente alterna.** Repetir 2013–2024 con la deforestación del SMByC.
8. **Muestra.** Excluir cuencas traslapadas o agrupar las centrales en cascada.

### 4.4 Valoración

- Energía valorada a precio de bolsa y, como alternativa, al precio de la época seca.
- Pesos constantes del último año disponible.
- Valor anual y valor presente, según lo que muestren los rezagos.
- Hectáreas sin doble conteo en cuencas compartidas.
- Lectura de política: cuánto del valor ocurre en cuencas de centrales que pagan transferencias y cuánto en centrales de menos de 10 MW, que no pagan.

### 4.5 Especificación fijada antes de estimar

Esta sección se congela antes de ver el primer resultado. Si algo cambia después, se anota aquí con fecha y razón, y la versión original se reporta igual. Así el resultado no depende de haber buscado la especificación que funciona.

**Estado: aprobada por el autor el 17 de noviembre de 2026.**

| Elemento | Definición fijada |
|---|---|
| Unidad | Central (o grupo de centrales que XM reporta juntas) por año |
| Variable dependiente | Factor de capacidad = generación anual (MWh) / (capacidad efectiva neta promedio del año × horas del año) |
| Deforestación, medida A (acumulado) | Fracción del bosque de la cuenca en 2000 perdida acumulada desde 2001 hasta el año t (%) |
| Deforestación, medida B (flujo) | Pérdida de bosque en el año t: hectáreas (como en 2019) y porcentaje del bosque de 2000 |
| Uso de las dos medidas | Ambas son principales y se reportan siempre lado a lado, en modelos separados. Ninguna se descarta según el resultado |
| Bosque | Píxeles con `treecover2000` ≥ 30 % (Hansen) |
| Lluvia | CHIRPS, precipitación anual promedio de la cuenca (mm) |
| Tipo de central | Embalse = 1 si la central tiene embalse de regulación según XM y la capa de embalses del IGAC; 0 si es a filo de agua |
| Efectos fijos | Planta y año |
| Errores estándar | Agrupados por sistema hídrico. Si hay menos de 30 grupos, se reporta además *wild cluster bootstrap* |
| Muestra principal | Las 60 centrales de 2019 (después de corregir nombres y agrupaciones), 2001–2015; luego 2001–2024 |
| Criterio de la hipótesis | Para cada medida: b1 < 0 con p < 0,05 (dos colas); prueba F de b1 + b2 = 0. Si las dos medidas no coinciden, se reporta y se discute, no se elige una |
| Pruebas | Todas las de la sección 4.3 se estiman y se reportan, salgan a favor o en contra |
| Software | R con `fixest` |

#### Registro de cambios a la especificación

| Fecha | Cambio | Razón |
|---|---|---|
| — | — | — |

---

## 5. Plan de trabajo

| Fase | Contenido | Carpeta |
|---|---|---|
| 0. Preparación | Estructura del repositorio, cuentas, alcance, aprobación de la sección 4.5 | — |
| 1. Tabla maestra | Una fila por central: código XM, nombre, capacidad por año, fecha de entrada, tipo, captación, río, sistema hídrico | `code/00_tabla_maestra` |
| 2. Cuencas | Oficiales del IGAC; delimitación propia para las demás; validación de áreas; sistemas hídricos | `code/01_cuencas` |
| 3. Variables por cuenca | Deforestación y lluvia (Earth Engine); generación, capacidad, caudales y volumen útil (XM) | `code/02_*` a `code/04_*` |
| 4. Panel | Unión, diccionario de datos, pruebas automáticas, comparación con `legacy_2019/data/DF.xlsx` | `code/05_panel` |
| 5. Estimación | Réplica de 2019 con datos corregidos; especificación de la sección 4.5; pruebas de la sección 4.3; valoración | `code/06_estimacion` |
| 6. Escritura | Versión 2.0 de la tesis, artículo, instrucciones de réplica | `output/`, `README.md` |

---

## 6. Decisiones tomadas (17 de noviembre de 2026)

| # | Tema | Decisión |
|---|---|---|
| 1 | Producto | Versión 2.0 de la tesis con repositorio público como documento largo; de ahí sale el artículo |
| 2 | Periodo | Replicar primero 2001–2015; extender a 2024 después |
| 3 | Muestra | Las mismas 60 centrales en la réplica. La tabla maestra incluye todas las hidráulicas de XM; ampliar la muestra es extensión o robustez |
| 4 | Herramienta | Python para descargas (pydataxm, Earth Engine); R con `fixest` para estimar |
| 5 | Cuencas del IGAC | Se usan los 37 certificados; los shapes se piden al Minambiente |
| 6 | Repositorio | Mismo repositorio, rama `tesis-2.0`; la versión de 2019 queda en la etiqueta `v2019` y en `legacy_2019/` |
| — | Archivos de Stata y `DF2.csv` | No aparecen. Se trabaja sin ellos |
| — | Medida de deforestación | Acumulado y flujo anual, las dos como principales (sección 4.5) |
| — | Script de GRASS | No se recupera. Las cuencas sin certificado se delimitan de nuevo con modelo de elevación |

---

## 7. Riesgo principal

El resultado puede cambiar. Con la lluvia corregida, efectos fijos de año y errores agrupados, el coeficiente de −13,7 puede bajar, perder significancia o sostenerse. Las tres salidas son publicables si el diseño es limpio. Por eso la sección 4.5 fija la especificación principal y las pruebas antes de estimar.

---

## 8. Fuentes

- [Global Forest Change v1.12, página de descarga](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html)
- [Global Forest Change v1.12 en Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12)
- [CHIRPS v3, Climate Hazards Center](https://chc.ucsb.edu/node/497)
- [CHIRPS v3, guía de datos de NCAR](https://climatedataguide.ucar.edu/climate-data/chirps-climate-hazards-infrared-precipitation-station-data-version-3)
- [API XM, repositorio oficial](https://github.com/EquipoAnaliticaXM/API_XM)
- [PARATEC, XM](https://paratec.xm.com.co/paratec/SitePages/generacion.aspx?q=capacidad)
- [IDEAM, hoja metodológica de cambio de bosque natural](https://bart.ideam.gov.co/indiecosistemas/ind/bosques/hm/HM%20Cambio%20bosque%20natural.pdf)
- [IGAC, hub de datos abiertos](https://datos-abiertos-igac-igac-oit.hub.arcgis.com/)
- [Capa Embalse del IGAC en datos.gov.co](https://www.datos.gov.co/dataset/Embalse/igd9-6s52)
- [Minambiente, decreto de transferencias del sector eléctrico](https://www.minambiente.gov.co/gobierno-nacional-expidio-el-decreto-que-actualiza-la-metodologia-para-distribuir-los-recursos-provenientes-del-sector-electrico/)
- [Tesis original, Universidad del Rosario](https://repository.urosario.edu.co/bitstreams/16f45fd3-c4e6-470c-acac-4c41f81ac0c7/download)
