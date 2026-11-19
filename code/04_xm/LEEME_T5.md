# T5 · Datos de XM — guía

Código en `03_codigo/03_xm/`, salidas en `02_datos/xm_procesado/`. Correr desde `03_tesis`.

## Paso 1. Descarga (en el Mac, una vez)

```bash
python3 -m pip install pandas openpyxl requests
python3 03_codigo/03_xm/descargar_xm_t5.py
```

Baja de la API pública de XM (servapibi.xm.com.co, con `requests`; `pydataxm` falla en Python 3.14), 2000-01-01 a 2024-12-31, **sin filtros** (todos los ríos y embalses del SIN; el filtro por unidad lo hace el procesamiento):

| Métrica XM | Entidad | Frecuencia | Para |
|---|---|---|---|
| `ListadoRios`, `ListadoEmbalses` | Sistema | lista | códigos y nombres para la relación río/embalse → unidad |
| `AporCaudal` | Rio | diaria | aportes en m3/s (pedidos 2 y 6) |
| `VoluUtilDiarMasa` | Embalse | diaria | volumen útil (pedido 3) |
| `PorcVoluUtilDiar` | Embalse | diaria | % de volumen útil → capacidad útil (pedido 5) |
| `CapaUtilDiarMasa` | Embalse | diaria | capacidad útil en m3 (pedido 5) |
| `PrecBolsNaci` | Sistema | horaria | precio de bolsa 2000–2024 (pedido 4; se baja entero para compararlo con los Excel viejos) |

Además: ONI de NOAA (`oni.ascii.txt`) e IPC anual del Banco Mundial como respaldo. Todo queda sin tocar en `02_datos/crudos/xm_t5/` y `02_datos/crudos/macro/`. Si se corta, se vuelve a correr y sigue donde iba.

**IPC oficial:** la descarga baja el IPC mensual del Banco de la República (serie 1.2.5, IPC total nacional del DANE, base dic-2018 = 100, empalmado desde 1954) a `02_datos/crudos/macro/ipc_banrep.xlsx`. Solo el IPC: `python3 03_codigo/03_xm/descargar_xm_t5.py --solo ipc`. Si BanRep no responde, descárgalo a mano desde su página "IPC – Serie histórica" (exportar a Excel) con ese mismo nombre, o el anexo de índices del DANE como `ipc_dane.xlsx`. El IPC del Banco Mundial queda solo como respaldo y el reporte lo marca REVISAR.

**Alternativa sin API (Sinergox, como hiciste con generación):** Hidrología → Aportes → "Aportes Caudal por Río" (diario, 2000–2024, todos los ríos); Hidrología → Reservas → "Volumen Útil Diario por Embalse" y "Porcentaje de Volumen Útil"; Transacciones → Precios → "Precio de Bolsa Nacional" (horario, 2019–2024). Si vas por aquí, avísame en el chat T5 para adaptar la lectura.

## Paso 2. Procesamiento

```bash
python3 03_codigo/03_xm/procesar_t5.py
```

Funciona con lo que haya. Sin la descarga, usa los archivos viejos (caudales 2000–2017, volumen 2000–ago-2018, precio 2000–2018) y deja las pruebas faltantes como PENDIENTE. Con la descarga completa 2019–2024 y compara las fuentes en los años que se traslapan.

Revisar `02_datos/xm_procesado/reporte_qc_t5.md`.

## Salidas

| Archivo | Contenido |
|---|---|
| `generacion_mensual_unidad.csv` | unidad × mes: MWh, días con registro, capacidad, FC; meses sin registro rellenados con 0 y marcados |
| `relacion_rio_unidad.csv` | ríos y embalses XM de cada unidad; tipo de asignación |
| `aportes_rio_mensual.csv`, `aportes_rio_diario.csv.gz` | caudal por río XM |
| `aportes_unidad_mensual.csv` | caudal de la cuenca total de cada unidad (m3/s) |
| `escorrentia_unidad.csv` | control: caudal / área ATCH / lluvia CHIRPS |
| `volumen_util_embalse_diario.csv.gz`, `volumen_util_unidad_mensual.csv` | volumen útil (m3) |
| `capacidad_util_embalse.csv`, `regulacion_unidad.csv` | capacidad útil y regulación (años y días de aporte medio almacenables) |
| `variabilidad_caudal_unidad_anio.csv` | CV mensual, mínimo y máximo relativos; con datos diarios, CV diario, p10/p90 y Q7 mínimo |
| `precio_bolsa_diario/mensual/anual.csv` | $/kWh, promedio simple de las 24 horas |
| `oni_mensual.csv`, `oni_anual.csv`, `ipc_mensual.csv`, `ipc_anual.csv` | controles y deflactor (pesos de 2024) |

## Reglas

- **Ríos por unidad.** `rios_xm` = los que XM asigna a la planta (`Rio-planta-embalse.xlsx`, 2018). `rios_total` = todos los ríos XM dentro de la ATCH: en cascadas XM asigna solo la cuenca intermedia (Porce III, Porce II, San Francisco, Betania "CP"), lo que no corresponde al área donde se mide la deforestación. Se usa `rios_total`. Comprobado con el coeficiente de escorrentía: con los ríos de XM, San Francisco daba 0,06 y Porce III 0,07; con la cuenca total, 0,55 y 0,41.
- **Unidades sin río propio:** si su ATCH ocupa al menos 25 % de una cuenca contenedora con serie, se usa esa serie escalada por área (`proxy_anidada`); si no, `sin_rio`.
- **Regulación** = capacidad útil (m3) / (aporte medio 2000–2024 × segundos del año). Filo = 0. Embalse sin embalse en XM = vacío, para decidir.
- **Capacidad útil:** volumen útil / % de volumen útil (API). Mientras no esté la descarga, provisional: percentil 99 del volumen observado 2000–2018.
