# Plan para volver a correr la tesis

**El efecto de la deforestación en la generación de energía hidroeléctrica: evidencias en el territorio colombiano**
Jorge Enrique Rojas Sánchez · plan elaborado el 16 de noviembre de 2026 · decisiones registradas el 17 y 18 de noviembre de 2026

> Las rutas que empiezan por `03_tesis/` o `02_datos/` son de la carpeta de trabajo del autor, no de este repositorio. El código de cada etapa está en `code/` (ver `code/README.md`).
>
> **Versión sellada antes de estimar:** la etiqueta `pre-estimacion` (19-nov-2026) marca el estado de este plan, de la especificación de la sección 4.5 y del código de los datos antes de correr cualquier regresión. Cualquier cambio posterior queda en el registro de cambios de 4.5 y en el historial de git.

---

## 1. Decisión de fondo

No conviene reparar la base de 2019. Conviene reconstruirla desde fuentes públicas, con código que cualquiera pueda volver a ejecutar, y estimar de nuevo.

Razones:

- El script que produjo las tablas publicadas no aparece. Hoy la tesis no es replicable ni por su autor.
- La base tiene errores confirmados (sección 2) que afectan los coeficientes.
- Todos los insumos tienen hoy una versión pública mejor que la de 2019, y casi todos llegan hasta 2024. El panel puede pasar de 15 a 24 años.
- Para un artículo, un revisor va a pedir exactamente lo que faltó: efectos fijos de año, errores agrupados, deforestación acumulada y evidencia del mecanismo.

La pregunta, la hipótesis y el diseño central no cambian: ¿la deforestación de la cuenca reduce la generación de las centrales a filo de agua y no la de las centrales con embalse?

**Actualización 17-nov-2026:** ya no se replica la muestra de 2019. El estudio se hace con las centrales que tienen cuenca oficial del IGAC (ver 4.5 y registro de cambios).

---

## 2. Qué falló en 2019 y cómo se evita

| Problema encontrado | Evidencia | Cómo se evita ahora |
|---|---|---|
| Lluvia inválida en 2011, 2012 y 2013 | Todas las cuencas valen entre 11 y 12 esos años, frente a 740–5.790 mm en los demás. Las 788 observaciones de las tablas indican que esos años sí entraron a la regresión | Lluvia satelital (CHIRPS) para toda la serie, con una prueba automática de rangos por año |
| No hay script de estimación | El R disponible solo tiene modelos exploratorios en logaritmos; splines y kernel no están | Un solo flujo de código versionado, de datos crudos a tablas |
| Efectos fijos de año declarados pero no estimados | Las tablas reportan coeficiente para el precio de bolsa, que solo varía por año | Efectos fijos de planta y de año; el precio sale del modelo |
| Sin errores agrupados | Las tablas no los reportan | Agrupar por sistema hídrico (variante A, sección 4.5) |
| Deforestación medida en grilla de 208 m | 4,34 ha por celda, en vez de los 30 m originales | Conteo a resolución nativa, dentro de la máscara de bosque del año 2000 |
| Áreas de cuenca subestimadas en ~19 % (hallado en T3, 17-nov-2026) | En 11 centrales con la misma cuenca que la oficial, la razón ATCH/2019 es ≈ 1,23: coincide con contar cada celda como 4,34 ha cuando las celdas de 7,5" miden ~5,35 ha | Áreas oficiales del IGAC; hectáreas a 30 m en Earth Engine (T4: diferencia máxima con el certificado, 0,16 %) |
| Factores de capacidad mayores que 1 | Máximo de 1,32; capacidad mal declarada (Río Grande) | Capacidad efectiva neta de XM, variable en el tiempo |
| Cuencas mal delimitadas | San Carlos (1.240 MW) con 178 ha; Jaguas con 3.394 ha; Chinchiná con un tercio del área oficial; Río Grande con la cuenca del embalse Riogrande II | Delimitación oficial del IGAC; validación de áreas |
| Emparejamiento de nombres | Alto y Bajo Anchicayá sin generación; "Albán" sin cuenca | Tabla maestra de centrales con el código de recurso de XM como llave |
| Muestra y tipos inconsistentes | 36 centrales de filo en la Tabla 2, 24 en la Tabla 6; hoja de tipos de una muestra anterior de 55 | Tipo de central tomado de una fuente única y documentado por planta |
| Otros errores hallados en T2 (17-nov-2026) | Chivor asignada a la cadena del río Bogotá; Río Piedras confundida con Florida II; capacidades erradas en Amalfi, Ínsula, Nima, Piedras Blancas y Puente Guillermo; fechas de entrada erradas en Urrá, El Quimbo y Amoyá | Tabla maestra con decisiones documentadas en `decisiones_jorge.csv` |

---

## 3. Datos públicos disponibles

### 3.1 Verificados en esta búsqueda

| Insumo | Fuente | Cobertura | Acceso | Notas para la tesis |
|---|---|---|---|---|
| Pérdida de bosque | Hansen et al., Global Forest Change v1.12 | 2000–2024, 30 m | [Descarga por teselas](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html) · [Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12) | Capas `lossyear` y `treecover2000`. El algoritmo cambió hacia 2011; la serie no es del todo homogénea antes y después. Los efectos fijos de año absorben el salto común |
| Lluvia | CHIRPS v3 (UC Santa Barbara) | 1981–presente, 0,05° (≈5,5 km), diaria y mensual | [Portal CHC](https://www.chc.ucsb.edu/data) · [Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHC_CHIRPS_V3_DAILY_RNL) | Reemplaza la interpolación de estaciones. Permite separar época seca y de lluvias |
| Lluvia de estaciones | IDEAM, DHIME | Histórico por estación | [DHIME](http://dhime.ideam.gov.co/atencionciudadano/) · [Precipitación nacional diaria (zip)](http://bart.ideam.gov.co/PQRS/AQTSUtils/PrecipitacionNacionalDiaria.zip) | Para validar CHIRPS en algunas cuencas, no como fuente principal |
| Generación, precio de bolsa, capacidad efectiva neta, aportes, volumen útil | XM | Desde 2000 | [API XM y pydataxm](https://github.com/EquipoAnaliticaXM/API_XM) · SiMEM · Sinergox | Jorge descargó generación horaria 2000–2024 y capacidad diaria 2007–2024 (`03_tesis/02_datos/Generacion` y `Capacidad`); procesadas en `02_datos/xm_procesado`. Caudales, volumen útil, capacidad útil y precio (T5) se descargan de la API de XM directamente con `requests`, no con `pydataxm` (falla en Python 3.14) |
| Listado y capacidad de plantas en operación | XM, PARATEC | Vigente | [PARATEC generación](https://paratec.xm.com.co/paratec/SitePages/generacion.aspx?q=capacidad) | Para la tabla maestra: nombre oficial, capacidad, tipo, fecha de entrada |
| Deforestación oficial | IDEAM, SMByC | Anual solo desde 2013; antes, periodos irregulares (2000–2005, 2005–2010, 2010–2012) | [SMByC](http://smbyc.ideam.gov.co/) | No sirve para el panel anual completo. Sí como robustez 2013–2024 y para las cifras de contexto |
| Embalses y cartografía básica | IGAC, datos abiertos | Nacional | [Hub de datos abiertos IGAC](https://datos-abiertos-igac-igac-oit.hub.arcgis.com/) · [Capa Embalse en datos.gov.co](https://www.datos.gov.co/dataset/Embalse/igd9-6s52) | Licencia CC BY 4.0. Sirve para confirmar qué centrales tienen embalse |
| Área drenada (validación de cuencas) | MERIT Hydro v1.0.1 en Earth Engine | Global, 90 m | `MERIT/Hydro/v1_0_1` | Usada en T4 para validar las ATCH |

### 3.2 Cuencas oficiales del IGAC

La norma de transferencias del sector eléctrico asigna al IGAC la delimitación de las áreas de cuenca y embalse de cada central.

**Estado al 17 de noviembre de 2026:**

- El reporte del IGAC del 30 de octubre de 2026 tiene **34 proyectos en estado "ok"**, 27 en revisión ("Rev") y 21 sin radicar. Jorge tiene además 37 certificados en `03_tesis/02_datos/IGAC_certificados`.
- Los **shapes** llegaron (37 proyectos, en `02_datos/IGAC_cuencas`). Se usa la cuenca hidrográfica total (ATCH) de cada certificado; extracción y validación en T3 (`02_datos/cuencas_igac`). No se hará PQRSD al IGAC.
- En el artículo, cada cuenca oficial se cita por el número de radicado de su certificado. Así un tercero sabe qué documento pedir.

Precauciones:

- **Cubren solo centrales de más de 10 MW**, las obligadas a transferir, salvo algunas menores que las empresas radicaron.
- **Definen la cuenca para efectos fiscales**, no necesariamente la cuenca aportante hidrológica hasta la captación. La ATCH de Miel I incluye los trasvases Guarinó y Manso.
- Algunas centrales están agrupadas en XM (Guadalupe III + IV + Troneras = GUATRON; Pajarito I + II = PAJARITO; Alto + Bajo Anchicayá = ALBAN). En el panel se tratan como una sola unidad, porque XM reporta la generación conjunta; su cuenca es la unión de las ATCH de sus proyectos.

**Validación con MERIT Hydro (T4, 17-nov-2026).** Dentro de cada ATCH se buscó el píxel de mayor área drenada y se comparó con el área de la ATCH (`02_datos/earth_engine/validacion_merit.csv`). 23 de 34 unidades tienen una sola salida coherente (razón 0,9–1,1). Las demás tienen razón menor: Pajarito y Guatron (uniones de proyectos), Miel I (trasvases Guarinó y Manso), Esmeralda, San Francisco e Ínsula (cadena Chinchiná), Amoyá, Porce III y PCH Porce III (0,89), y fuera de la muestra Tunjita y Chivor. **Decisión de Jorge:** la ATCH se usa tal como la certificó el IGAC. Las delimitaciones se revisaron central por central con el IGAC y el IGAC las verificó con cada empresa antes de certificarlas. Un área trasvasada aporta agua a la central, así que su deforestación debe contarse. La razón menor que 1 refleja trasvases o varias captaciones, no un error de delimitación. En el artículo se explica en el anexo de cuencas.

Qué hacer con ella:

1. Usarla como delimitación de la muestra principal (sección 4.5).
2. Validación con modelo de elevación: hecha con MERIT Hydro en Earth Engine (ver arriba).
3. Validar el método propio contra la oficial en las centrales donde existan las dos.

### 3.3 Fuentes que conozco pero no verifiqué hoy

Confirmar disponibilidad antes de depender de ellas.

| Insumo | Fuente probable | Uso |
|---|---|---|
| Cuencas de referencia | HydroBASINS; zonificación hidrográfica del IDEAM | Validación |
| Fenómeno de El Niño | Índice ONI de NOAA | Control y pruebas de robustez; control en las regresiones por unidad |
| Índice de precios | DANE o Banco de la República | Llevar la valoración a pesos constantes actuales |
| Ubicación y atributos de centrales | UPME (SIMEC) | Coordenadas de captación |
| Costos de oportunidad | CONPES 3886 y sus fuentes (DANE, Agronet) | Comparación con el valor por hectárea |

---

## 4. Diseño nuevo del estudio

### 4.1 Lo que cambia

| Elemento | Tesis 2019 | Versión nueva |
|---|---|---|
| Muestra | 60 centrales, cuencas propias | Centrales con cuenca oficial del IGAC (estado ok), sin plantas de acueducto; se amplía cuando lleguen más |
| Periodo | 2001–2015 | 2001–2024 |
| Frecuencia | Anual | Anual y mensual (para separar época seca) |
| Deforestación | Flujo anual, grilla de 208 m | Flujo anual y acumulado desde 2000, a 30 m, sobre el bosque existente en 2000 |
| Lluvia | Interpolación de estaciones | CHIRPS promedio de cuenca; anual, de época seca y anomalía |
| Capacidad | Fija, de varias fuentes | Capacidad efectiva neta de XM, variable en el tiempo |
| Tipo de central | Indicadora filo / embalse | Indicadora, más una medida continua de regulación (volumen útil sobre aporte medio) |
| Efectos fijos | Planta | Planta y año |
| Errores | Sin agrupar | Agrupados por sistema hídrico (variante A, 10 sistemas) con *wild cluster bootstrap* |
| Verificación individual | No había | Regresiones por unidad e influencia de cada unidad y sistema (4.3, punto 9) |
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
3. **Época seca.** El mecanismo predice que el efecto se concentra en los meses secos. Es la prueba más directa de la regulación hídrica. Panel mensual; época seca principal: los 4 meses más secos de cada cuenca según la climatología CHIRPS 2001–2024; robustez: diciembre–marzo (fijado el 18-nov-2026, ver registro).
4. **Placebo temporal.** La deforestación futura no debe explicar la generación presente. Si la explica, hay un factor omitido.
5. **Sin años de El Niño.** Excluir 2009–2010, 2015–2016 y 2023–2024 y ver si el resultado se sostiene.
6. **Caudales.** Con los aportes de XM, medir si la variabilidad del caudal aumenta con la deforestación. Es observar el mecanismo en vez de inferirlo. Solo series de XM (sin IDEAM), todas las unidades con serie. Medida principal: coeficiente de variación del caudal diario; segunda: caudal base (mínimo de 7 días sobre la media) (fijado el 18-nov-2026).
7. **Fuente alterna.** Repetir 2013–2024 con la deforestación del SMByC.
8. **Muestra.** Excluir cuencas traslapadas o agrupar las centrales en cascada. Excluir los años con factor de capacidad mayor que 1. Excluir los meses sin registro de generación en XM (tomados como 0). Incluir los años de operación parcial con el FC sobre las horas en operación. Sin Miel I 2001–2013.
9. **Análisis individuales (verificación).** Decisión de Jorge, 17-nov-2026:
   - **Regresión por unidad**, 2001–2024 (o desde su entrada): FC sobre deforestación (las dos medidas), lluvia, índice ONI y tendencia lineal; una sola unidad no admite efectos fijos de año. Se reporta la distribución de los coeficientes por tipo (filo / embalse), su promedio ponderado por precisión y cuántos tienen el signo esperado. Con unos 24 años por unidad la potencia individual es baja: muestra si el efecto del panel es general o lo empujan pocas unidades; no reemplaza al panel.
   - **Influencia:** estimar el modelo principal quitando una unidad a la vez y un sistema hídrico a la vez.
   - **Errores alternativos:** agrupados por unidad, y por sistema hídrico en la variante B (Ituango no une a sus afluentes de cabecera; 14 sistemas).

### 4.4 Valoración

- Energía valorada a precio de bolsa y, como alternativa, al precio de la época seca.
- Pesos constantes del último año disponible.
- Valor anual y valor presente, según lo que muestren los rezagos.
- Hectáreas sin doble conteo en cuencas compartidas (`02_datos/cuencas_igac/hectareas_por_unidad.csv`: suma simple 8,37 millones de ha; unión 6,33 millones).
- Lectura de política: cuánto del valor ocurre en cuencas de centrales que pagan transferencias.

### 4.5 Especificación fijada antes de estimar

Esta sección se congela antes de ver el primer resultado. Si algo cambia después, se anota en el registro de cambios con fecha y razón, y la versión original se reporta igual. Así el resultado no depende de haber buscado la especificación que funciona.

**Estado: aprobada por Jorge el 17 de noviembre de 2026; muestra y agrupación de errores modificadas el mismo día; decisiones de T5 (17-nov) y T6 (18-nov) agregadas antes de estimar (ver registro). Panel listo en `02_datos/panel/` (T6). Sellada con la etiqueta `pre-estimacion` el 19-nov-2026.**

| Elemento | Definición fijada |
|---|---|
| Unidad | Central (o grupo de centrales que XM reporta juntas) por año |
| Variable dependiente | Factor de capacidad = generación anual (MWh) / (capacidad efectiva neta promedio del año × horas del año), con la capacidad declarada por XM. Si el factor pasa de 1, se conserva (se le cree a la generación) y se anota |
| Deforestación, medida A (acumulado) | Fracción del bosque de la cuenca en 2000 perdida acumulada desde 2001 hasta el año t (%) |
| Deforestación, medida B (flujo) | Pérdida de bosque en el año t: hectáreas y porcentaje del bosque de 2000 |
| Uso de las dos medidas | Ambas son principales y se reportan siempre lado a lado, en modelos separados. Ninguna se descarta según el resultado |
| Bosque | Píxeles con `treecover2000` ≥ 30 % (Hansen) |
| Lluvia | CHIRPS, precipitación anual promedio de la cuenca (mm) |
| Cuenca | Delimitación oficial del IGAC: cuenca hidrográfica total (ATCH) del certificado, incluidas las áreas trasvasadas; para unidades agrupadas, la unión de las ATCH de sus proyectos |
| Tipo de central | Embalse = 1 si la central tiene embalse de regulación propio o está regulada por un embalse aguas arriba ("embalse por cadena": Riogrande I, Río Grande, Ínsula); 0 si es a filo de agua. Clasificación por planta en la tabla maestra |
| Control de trasvase | Miel I: fracción del año con el trasvase Guarinó activo (desde dic-2010) y con el trasvase Manso activo (desde jun-2013); 0 en las demás unidades. Entra en todas las especificaciones |
| Efectos fijos | Planta y año |
| Errores estándar | Agrupados por sistema hídrico, **variante A** (`sistema_geom_A` en `02_datos/cuencas_igac/sistemas_hidricos.csv`): dos unidades están en el mismo sistema si comparten más del 5 % de la cuenca ATCH menor, encadenando las cuencas anidadas. Hoy 10 sistemas. Como hay menos de 30 grupos, se reporta siempre además *wild cluster bootstrap* |
| Muestra principal | Unidades con delimitación del IGAC en estado "ok", excepto plantas de acueducto, 2001–2024 (o desde su entrada), sin los años de operación parcial (año de entrada a mitad de año, año de salida, años en que XM empieza a reportar la planta después del 1 de enero). Meses sin registro de generación en XM = 0. Al 17-nov-2026: 26 unidades (14 embalse, 12 filo) en 10 sistemas hídricos (variante A). Se amplía cuando el IGAC pase más proyectos a "ok"; cada ampliación se fecha y se reporta también la estimación con la muestra anterior |
| Criterio de la hipótesis | Para cada medida: b1 < 0 con p < 0,05 (dos colas); prueba F de b1 + b2 = 0. Si las dos medidas no coinciden, se reporta y se discute, no se elige una |
| Pruebas | Todas las de la sección 4.3, incluidos los análisis individuales (punto 9), se estiman y se reportan, salgan a favor o en contra |
| Software | R con `fixest` |

**Registro de cambios a la especificación**

| Fecha | Cambio | Razón |
|---|---|---|
| 17-nov-2026 | Muestra principal: de "las 60 centrales de 2019, 2001–2015" a "unidades con delimitación IGAC ok, sin acueducto, 2001–2024" | Decisión de Jorge: no replicar la tesis, trabajar con cuencas oficiales. Se toma antes de construir el panel y sin ver resultados |
| 17-nov-2026 | Se excluyen las plantas de acueducto (Niquía, La Ayurá, Manantiales, Santa Ana, Nima, Piedras Blancas y microcentrales de EPM) | Su generación la define la demanda de agua potable, no la hidrología de la cuenca |
| 17-nov-2026 | Se excluyen además Intermedia y Sancancio: muestra principal de 28 a 26 unidades | Plantas de acueducto, confirmado por EPM a Jorge. Sin ver resultados |
| 17-nov-2026 | Sistema hídrico para agrupar errores: variante A, derivada de la geometría de las ATCH (10 sistemas), en lugar de los 16 propuestos a mano en la tabla maestra. Se agregan como verificación la variante B, los errores por unidad y las regresiones por unidad (4.3, punto 9) | Decisión de Jorge. Las cuencas anidadas comparten choques hidrológicos y A es la agrupación más conservadora; los análisis individuales verifican que el resultado no dependa de pocas unidades. Sin ver resultados |
| 17-nov-2026 | Factor de capacidad mayor que 1 se conserva | Decisión de Jorge: se le cree a la generación; nota en el paper y prueba sin esos años (4.3, punto 8) |
| 17-nov-2026 | RIO GRANDE pasa de filo a embalse: muestra 14 embalse / 12 filo | Decisión de Jorge (T2), sin ver resultados |
| 17-nov-2026 | La cuenca es la ATCH certificada incluidas las áreas trasvasadas, aunque MERIT muestre varias salidas (aclaración, no cambio) | Decisión de Jorge tras la validación con MERIT (3.2). Solo se miró la deforestación y el área drenada, no la generación |
| 17-nov-2026 | Se agrega una medida continua de regulación (capacidad útil / aporte medio, en días) como prueba secundaria; no reemplaza la indicadora de embalse | Decisión de Jorge (T5): se construye solo con los datos de XM ya descargados, sin buscar otras fuentes. Sin ver resultados |
| 17-nov-2026 | Prueba de caudales (4.3.6) solo con series de XM, sin estaciones del IDEAM, con todas las unidades que tienen serie (no solo filo) | Decisión de Jorge (T5): las estaciones del IDEAM suelen traer errores. Sin ver resultados |
| 17-nov-2026 | "Embalse por cadena": Riogrande I, Río Grande e Ínsula son embalse porque los regula un embalse aguas arriba de su cadena (aclaración de la definición de tipo) | Decisión de Jorge (T5). Riogrande I y Río Grande toman la regulación de Riogrande II; Ínsula queda sin valor de regulación. Sin ver resultados |
| 17-nov-2026 | Meses sin registro de generación en XM = paradas (0), marcados (`mes_sin_registro`) para una robustez que los excluye | Decisión de Jorge (T5): pueden ser ventas por fuera del SIN. Sin ver resultados |
| 18-nov-2026 | Época seca (4.3.3): principal = los 4 meses más secos de cada cuenca según la climatología CHIRPS 2001–2024; robustez = diciembre–marzo | Decisión de Jorge (T6). En 14 de las 26 cuencas los 4 meses más secos no coinciden con dic–mar (régimen bimodal, con un segundo verano entre junio y septiembre). Se miró solo la lluvia. Sin ver resultados |
| 18-nov-2026 | Miel I: ATCH completa todo el periodo (decisión 11) y control de trasvase activo (Guarinó desde dic-2010, Manso desde jun-2013) en todas las especificaciones; robustez sin Miel I 2001–2013 | Decisión de Jorge (T6). El agua trasvasada sube la generación de Miel I desde 2011 y coincide con años de más deforestación acumulada; sin el control, ese salto se le atribuiría a la deforestación. Sin ver resultados |
| 18-nov-2026 | Años de operación parcial fuera de la estimación principal (14 unidad-año: años de entrada, Sonsón 2022, 2003 de Caracolí, Riofrío y Sonsón); robustez que los incluye con el FC sobre las horas en operación | Decisión de Jorge (T6). Con las horas del año completo el FC de esos años sale cercano a 0 (Porce III 2010: 0,0002) y no refleja hidrología. Sin ver resultados |
| 18-nov-2026 | Prueba de caudales (4.3.6): medida principal = coeficiente de variación del caudal diario; segunda = caudal base (mínimo de 7 días / media); las demás al anexo | Decisión de Jorge (T6): fijar la medida antes de estimar. Sin ver resultados |
| 18-nov-2026 | Aclaraciones de T6, sin cambio de regla: Caracolí 2021–2022 (XM sin ningún registro en el año) entra con generación 0 por la regla de meses sin registro, marcado; Sonsón 2023–2024 queda fuera (salió de operación en abr-2022) | Aplicación de las reglas ya fijadas al armar el panel. Sin ver resultados |
| 19-nov-2026 | Sin cambio de especificación: se sella el plan y el código de datos (T2–T6) con la etiqueta `pre-estimacion` | Constancia pública, con fecha, de que la especificación se fijó antes de estimar |
| 19-nov-2026 | IPC oficial del DANE (variación anual dic–dic, encadenada en un índice de fin de año) en lugar del IPC del Banco Mundial para llevar el precio de bolsa a pesos de 2024. Solo cambian `factor_a_pesos_2024` y `precio_bolsa_cop2024_kwh`; ninguna variable del modelo principal | Pendiente de T5. Afecta solo la valoración (4.4). Hecho después de la etiqueta y antes de estimar. Sin ver resultados |

---

## 5. Plan de trabajo

### Fase 0. Preparación

| Tarea | Estado |
|---|---|
| Crear el proyecto y la estructura de carpetas | Cerrado: rama `tesis-2.0` |
| Buscar los archivos de Stata y `DF2.csv` en el Mac mini | Cerrado: no aparecen. Se trabaja sin ellos |
| Definir el alcance | Cerrado: ver secciones 4.5 y 8 |
| Cuenta de Earth Engine | Cerrado |
| Cuencas oficiales | Cerrado: shapes y certificados de 37 proyectos; ATCH extraídas (T3) |
| Aprobar la sección 4.5 | Cerrado; muestra y agrupación de errores modificadas el 17-nov-2026 |
| Base de 2019 | Encontrada: `DF.xlsx`; queda como referencia |

### Fase 1. Tabla maestra de centrales

Hecha (T2). Una fila por unidad con código XM, capacidad efectiva neta por año, fecha de entrada, tipo, coordenadas, río, sistema hídrico, estado IGAC y marca de acueducto. Código en `code/00_tabla_maestra/`.

### Fase 2. Cuencas

| Tarea | Tú | Claude |
|---|---|---|
| Conseguir los shapes oficiales | Hecho | Hecho: ATCH extraídas y validadas contra los certificados |
| Validar | Hecho: ATCH confirmadas, trasvases incluidos | Hecho contra 2019, contra la versión de 2025 y con MERIT Hydro (T4) |
| Agrupar cuencas traslapadas | Hecho: variante A | Hecho: `sistemas_hidricos.csv`, `traslapes_unidades.csv`, `hectareas_por_unidad.csv` |

Código en `code/01_cuencas/`.

### Fase 3. Variables por cuenca

| Tarea | Tú | Claude |
|---|---|---|
| Deforestación 2001–2024 | Hecho en Earth Engine (17-nov) | Hecho: `code/02_deforestacion/`; 15 pruebas de calidad OK |
| Lluvia mensual 2000–2024 | Hecho | Hecho: mismo script de Earth Engine (`code/02_deforestacion/`) |
| Generación mensual y anual | Hecho con los Excel de XM | Hecho: `code/00_tabla_maestra/` y `code/04_xm/` |
| Caudales y volumen útil | Hecho (18-nov) | Hecho (T5): `code/04_xm/` |

### Fase 4. Panel y controles de calidad

| Tarea | Tú | Claude |
|---|---|---|
| Armar el panel | Hecho (18-nov): decisiones de época seca, Miel I, años parciales y caudales | Hecho (T6): `code/05_panel/` (panel anual y mensual, diccionario) |
| Pruebas automáticas | Revisar el reporte | Hecho: `reporte_qc_t6.md` (45 OK, 7 informativas, 2 para revisar) y conteo de observaciones por especificación |
| Comparar con 2019 | Interpretar diferencias | Hecho: `anexo_comparacion_2019.md` (19 centrales comunes) |

### Fase 5. Estimación

| Tarea | Tú | Claude |
|---|---|---|
| Especificación principal y pruebas de la sección 4.3 | Decidir cuáles van al texto y cuáles al anexo | Estimar, tabular y graficar, incluidas las regresiones por unidad |
| Valoración | Validar supuestos de precio | Calcular escenarios y sensibilidad |

### Fase 6. Escritura y publicación

| Tarea | Tú | Claude |
|---|---|---|
| Documento | Revisar argumento, política y normas | Redactar a partir del borrador 2.0, con tablas y figuras nuevas |
| Repositorio | Publicar | README, instrucciones de réplica, licencia |
| Artículo y difusión | Elegir revista; publicar en LinkedIn | Adaptar el texto al formato de la revista; resumen en inglés |

---

## 6. Estructura del proyecto

```
hidroeconomia-deforestacion/
├── README.md
├── PLAN.md                      # este archivo
├── data/
│   ├── raw/                     # descargas sin tocar (no se versionan)
│   ├── interim/                 # tablas intermedias
│   └── processed/               # panel final y diccionario
├── code/
│   ├── 00_tabla_maestra/        # T2
│   ├── 01_cuencas/              # T3
│   ├── 02_deforestacion/        # T4: deforestación, lluvia y validación MERIT (Earth Engine)
│   ├── 03_lluvia/               # (la lluvia se calcula en 02_deforestacion)
│   ├── 04_xm/                   # T5
│   ├── 05_panel/                # T6
│   ├── 06_estimacion/           # T7
│   └── 07_figuras_tablas/
├── output/
│   ├── tablas/
│   └── figuras/
├── docs/                        # visor web
└── legacy_2019/                 # scripts y base originales, sin cambios
```

---

## 7. Decisiones tomadas (17 y 18 de noviembre de 2026)

| # | Tema | Decisión |
|---|---|---|
| 1 | Producto | Ambos: versión 2.0 de la tesis con repositorio público como documento largo; de ahí sale el artículo, que es la meta |
| 2 | Periodo | 2001–2024 (ya no hay réplica 2001–2015) |
| 3 | Muestra | **Cambiada:** unidades con delimitación del IGAC en estado ok, sin plantas de acueducto (26 al 17-nov-2026). Se amplía a medida que el IGAC entregue más delimitaciones. Ya no se replican las 60 de 2019 |
| 4 | Herramienta | Python para datos (Excel y API de XM, Earth Engine); R con `fixest` para estimar |
| 5 | Earth Engine | Cuenta propia del autor |
| 6 | Cuencas del IGAC | Cuenca hidrográfica total (ATCH) de los certificados en estado ok. Sin PQRSD al IGAC |
| 7 | Unidades agrupadas | ALBAN (Alto + Bajo Anchicayá), GUATRON, PAJARITO como una unidad; Prado IV aparte de Prado, como en XM |
| 8 | Capacidad | La declarada por XM, promedio del año; si el FC pasa de 1 se le cree a la generación |
| 9 | Acueducto | Las plantas de acueducto salen del análisis (incluidas Intermedia y Sancancio, confirmadas por EPM); la evidencia queda en la tabla maestra |
| 10 | Sistemas hídricos | Variante A (10 sistemas, desde la geometría de las ATCH) para agrupar errores; variante B, errores por unidad, regresiones por unidad e influencia como verificación (4.3, punto 9) |
| 11 | Trasvases y validación MERIT | La ATCH certificada se usa tal cual, con las áreas trasvasadas. Las delimitaciones las revisó Jorge con el IGAC central por central y el IGAC las verificó con cada empresa. Una razón MERIT menor que 1 se lee como trasvase o varias captaciones (3.2) |
| — | Archivos de Stata y `DF2.csv` | No aparecen. Se trabaja sin ellos |
| — | Base de 2019 | `DF.xlsx`; solo como referencia y anexo |
| — | Medida de deforestación | Acumulado y flujo anual, las dos como principales (sección 4.5) |

---

## 8. Riesgo principal

El resultado puede cambiar. Con la lluvia corregida, efectos fijos de año, errores agrupados y una muestra distinta, el coeficiente de −13,7 puede bajar, perder significancia o sostenerse. Las tres salidas son publicables si el diseño es limpio. Con 26 unidades y 10 sistemas hídricos la potencia es menor que en 2019; por eso se reporta el *wild cluster bootstrap*, se verifica con los análisis individuales y la muestra crece a medida que lleguen delimitaciones.

---

## 9. Fuentes consultadas

- [Global Forest Change v1.12, página de descarga](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html)
- [Global Forest Change v1.12 en Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12)
- [Nota sobre el cambio de método de GFC hacia 2011](https://www.rdocumentation.org/packages/mapme.biodiversity/versions/0.9.5/topics/gfw_lossyear)
- [CHIRPS v3, Climate Hazards Center](https://chc.ucsb.edu/node/497)
- [CHIRPS v3, guía de datos de NCAR](https://climatedataguide.ucar.edu/climate-data/chirps-climate-hazards-infrared-precipitation-station-data-version-3)
- [CHIRPS v3 diario en Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHC_CHIRPS_V3_DAILY_RNL)
- [API XM, repositorio oficial](https://github.com/EquipoAnaliticaXM/API_XM)
- [SiMEM, portal de datos abiertos del sector eléctrico](https://www.portafolio.co/energia/asi-funcionara-el-portal-de-datos-abiertos-del-sector-electrico-590259)
- [PARATEC, XM](https://paratec.xm.com.co/paratec/SitePages/generacion.aspx?q=capacidad)
- [IDEAM, hoja metodológica de cambio de bosque natural](https://bart.ideam.gov.co/indiecosistemas/ind/bosques/hm/HM%20Cambio%20bosque%20natural.pdf)
- [IDEAM, enlaces de datos hidrometeorológicos](https://ideam.gov.co/sites/default/files/transparencia/planeacion/oficio_120239050073204_00001.pdf)
- [IGAC, hub de datos abiertos](https://datos-abiertos-igac-igac-oit.hub.arcgis.com/)
- [Capa Embalse del IGAC en datos.gov.co](https://www.datos.gov.co/dataset/Embalse/igd9-6s52)
- [Delimitación de áreas por el IGAC en la norma de transferencias](https://www.gydconsulting.com/como-deben-distribuirse-las-transferencias-del-sector-electrico-expediente-consejo-de-estado-no-27555-del-2025/)
- [Minambiente, decreto de transferencias del sector eléctrico](https://www.minambiente.gov.co/gobierno-nacional-expidio-el-decreto-que-actualiza-la-metodologia-para-distribuir-los-recursos-provenientes-del-sector-electrico/)
- [Tesis original, Universidad del Rosario](https://repository.urosario.edu.co/bitstreams/16f45fd3-c4e6-470c-acac-4c41f81ac0c7/download)
