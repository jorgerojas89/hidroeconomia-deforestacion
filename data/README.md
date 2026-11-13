# Datos

## Incluidos en el repositorio

| Carpeta | Contenido | Fuente |
|---|---|---|
| `xm/` | Generación real 2000–2018, volumen útil 2000–2018, caudales medios de ríos del SIN, precio de bolsa nacional 2000–2018, capacidad efectiva neta, relación río-planta-embalse, compras en contratos | XM S.A. E.S.P. — portal de información del mercado (Sinergox) |
| `upme/` | Tablas de centrales hidráulicas, con ubicación y atributos | UPME (exportadas desde capas SIG) |

Se conservan como se descargaron entre 2018 y 2019, para reproducir el análisis.

## No incluidos (por tamaño): cómo obtenerlos

| Insumo | Fuente | Dónde ubicarlo para correr el código |
|---|---|---|
| Modelo digital de elevación (DEM) de Colombia | USGS (SRTM) — EarthExplorer | `data/espacial/DEM.tif` |
| Drenajes 1:100.000 (dobles y sencillos) | IGAC — Colombia en Mapas / datos abiertos | `data/espacial/drenajes_igac_100k/` |
| Precipitación anual 1970–2015 | IDEAM | `data/espacial/precipitacion/` |
| Pérdida de cobertura forestal | Hansen et al. (2013), *Global Forest Change* | `data/espacial/deforestacion/` |
