##################################################################################################
#  Delimitación de cuencas aportantes de centrales hidroeléctricas a partir de un DEM (SAGA GIS) #
#  Tesis: "El efecto de la deforestación en la generación de energía hidroeléctrica:             #
#          evidencias en el territorio colombiano" — Universidad del Rosario, 2019               #
#  Autor: Jorge Enrique Rojas Sánchez                                                            #
#                                                                                                #
#  Versión ordenada (2026) del script original de 2019 (ver code/original_2019/).                #
#  Cambios frente al original:                                                                   #
#   - Rutas relativas configurables (bloque 0) en lugar de rutas fijas de Windows.               #
#   - Lectura y buffers con 'sf' en lugar de rgdal / maptools / rgeos (retirados de CRAN, 2023). #
#   - Punto de cierre creado en coordenadas geográficas y reproyectado a UTM 18N.               #
#   - Proyección de la cuenca corregida a UTM zona 18 (el original heredaba la zona 10 del       #
#     ejemplo del curso) y eliminados objetos del ejemplo (Howe Sound) en el mapa final.         #
#  ESTADO: no se ha vuelto a ejecutar con los datos originales. Ver README, "Limitaciones".      #
##################################################################################################

# ---- 0. Configuración --------------------------------------------------------------------------
ruta_datos   <- "data/espacial"          # DEM.tif y carpeta 'drenajes_igac_100k/'
ruta_salidas <- "outputs/cuencas"        # aquí se guardan los rásteres SAGA y los polígonos
ruta_saga    <- Sys.getenv("SAGA_PATH")  # ej. "/usr/local/bin" o "C:/Program Files/SAGA"
buffer_m     <- 30000                    # radio (m) alrededor de la planta para recortar el DEM
dir.create(ruta_salidas, recursive = TRUE, showWarnings = FALSE)

library(raster)   # rásteres
library(sf)       # vectores (reemplaza rgdal, maptools y rgeos)
library(RSAGA)    # interfaz con SAGA GIS (puede requerir instalarse desde el archivo de CRAN)

crs_utm18 <- 32618  # WGS 84 / UTM zona 18N
myenv <- rsaga.env(workspace = ruta_salidas, path = ruta_saga)

# ---- 1. Datos de entrada -----------------------------------------------------------------------
# 1.1 DEM de Colombia
dem <- raster(file.path(ruta_datos, "DEM.tif"))

# 1.2 Drenajes IGAC 1:100.000 (dobles y sencillos), reproyectados a UTM 18N
drenajes_dobles    <- st_transform(st_read(file.path(ruta_datos, "drenajes_igac_100k", "Drenajes_Dobles.shp")), crs_utm18)
drenajes_sencillos <- st_transform(st_read(file.path(ruta_datos, "drenajes_igac_100k", "Drenajes_Sencillos.shp")), crs_utm18)

# 1.3 Punto de cierre de la cuenca (sitio de captación de la planta).
# Ejemplo: una planta del estudio. Para todas las plantas, leer un CSV con columnas Lon y Lat.
punto <- st_transform(st_sfc(st_point(c(-76.86698438, 3.533074389)), crs = 4326), crs_utm18)

plot(dem); plot(st_geometry(drenajes_dobles), add = TRUE, col = "blue")
plot(punto, add = TRUE, pch = 21, bg = "cyan")

# ---- 2. Delimitación de la cuenca con SAGA -----------------------------------------------------
# 2.1 Recortar el DEM alrededor del punto y escribirlo en formato SAGA
zona     <- st_buffer(punto, buffer_m)
dem_rec  <- crop(dem, as(st_transform(zona, crs(dem)), "Spatial"))
writeRaster(dem_rec, filename = file.path(ruta_salidas, "dem_recorte.sgrd"), format = "SAGA", overwrite = TRUE)

# 2.2 Rellenar sumideros (Wang & Liu, 2006)
rsaga.fill.sinks(in.dem  = file.path(ruta_salidas, "dem_recorte.sgrd"),
                 out.dem = file.path(ruta_salidas, "dem_relleno.sgrd"),
                 method  = "xxl.wang.liu.2006", minslope = 0.1, env = myenv)
dem_relleno <- raster(file.path(ruta_salidas, "dem_relleno.sdat"))
values(dem_relleno) <- ifelse(values(dem_relleno) < 0, NA, values(dem_relleno))

# 2.3 Área de drenaje acumulada
rsaga.topdown.processing(file.path(ruta_salidas, "dem_relleno.sgrd"),
                         out.carea = file.path(ruta_salidas, "area_drenaje.sgrd"), env = myenv)
area_drenaje <- raster(file.path(ruta_salidas, "area_drenaje.sdat"))

# 2.4 Ajustar el punto de cierre a la celda de mayor área de drenaje cercana
celdas  <- as.data.frame(raster::extract(area_drenaje, as(st_transform(punto, crs(area_drenaje)), "Spatial"),
                                         buffer = 500, cellnumbers = TRUE))
salida  <- xyFromCell(area_drenaje, celdas$cell[which.max(celdas$value)])

# 2.5 Celdas que drenan hacia el punto de cierre (cuenca aportante) y conversión a polígono
rsaga.geoprocessor(lib = "ta_hydrology", module = 4, env = myenv,
                   param = list(TARGET_PT_X = salida[1, 1], TARGET_PT_Y = salida[1, 2],
                                ELEVATION = file.path(ruta_salidas, "dem_relleno.sgrd"),
                                AREA = file.path(ruta_salidas, "cuenca.sgrd"), METHOD = 0))
rsaga.geoprocessor(lib = "shapes_grid", module = 6, env = myenv,
                   param = list(GRID = file.path(ruta_salidas, "cuenca.sgrd"),
                                POLYGONS = file.path(ruta_salidas, "cuenca.shp"),
                                CLASS_ALL = 0, CLASS_ID = 100, SPLIT = 0))

cuenca <- st_read(file.path(ruta_salidas, "cuenca.shp"))
st_crs(cuenca) <- crs(dem_relleno)

# ---- 3. Mapa -----------------------------------------------------------------------------------
png(file.path(ruta_salidas, "mapa_cuenca.png"), width = 1600, height = 1600, res = 200)
plot(dem_relleno, col = gray(seq(1, 0.2, by = -0.1)), legend.args = list(text = "Elevación (m)", side = 3, line = 1))
plot(st_geometry(st_transform(drenajes_sencillos, crs(dem_relleno))), add = TRUE, col = "lightblue")
plot(st_geometry(st_transform(drenajes_dobles,    crs(dem_relleno))), add = TRUE, col = "blue")
plot(st_geometry(cuenca), add = TRUE, border = "darkorange", lwd = 2)
plot(st_transform(punto, crs(dem_relleno)), add = TRUE, pch = 21, bg = "red")
dev.off()
