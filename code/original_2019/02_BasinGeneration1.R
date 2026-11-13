##################################################################################################
#                                                                                                #
#                                                                                                #
#     # Delimitación de cuencas hidrograficas (CH) de hidroelectricas a partir RSAGA             #
#     # JORGE ROJAS / UROSARIO                                                                   #
#     # jorge.rojas@urosario.edu.co                                                              #
#                                                                                                #
#                                                                                                #
#     INDICE                                                                                     #
#                                                                                                #
#     0.0   INPUT DE DATOS                                                                       #
#     0.1   Cargar DEM de Colombia                                                               #
#     0.2   Cargar drenajes en Colombia                                                          #
#     0.3   Cargar coordenadas de los puntos de cierre de las CH                                 #
#                                                                                                #
#     1.0   Delimitación de cuencas                                                              #
#     1.1   Construir raster en formato SAGA del DEM                                             #
#     1.1.1 Llena sumideros y cargar archivo                                                     #
#     1.2   Definir las áreas de drenaje y de la pendiente                                       #
#     1.3   Delimitar cuenca a partir del punto de interes                                       #
#     1.3.1 Loop  Ludicrous Speed (Construyendoooooooo)                                          #
#                                                                                                #
#                                                                                                #
##################################################################################################

###### Aprestamiento #############################################################################

rm(list = ls())
setwd("C:/Users/Jorge/OneDrive/TESIS MAESTRIA - HIDROECONOMICS/Shapes") ####REVISAR####
par(mfrow = c(1, 1), mar = c(5, 5, 5, 5))
library(raster)
library(maptools)
library(RSAGA)
library(GISTools)
require(sp) 
require(rgdal)
require(classInt)
require(RColorBrewer)
require(hexbin)
require(XML)
require(spdep)
require(ggmap)
require(rgeos)
require(ggplot2)
require(dplyr)

# raster, maptools, RSAGA, GISTools, sp, rgdal, ClassInt, RColorBrewer, hexbin, XML, spdep, ggmap, rgeos, ggplot2, dplyr ##
myenv = rsaga.env(workspace = getwd(), path = "C:/Users/Jorge/Desktop/saga-7.0.0_x64")

myenv
CRSutm <- CRS('+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0')
#####   de drenajes +proj=longlat +ellps=GRS80 +no_defs

##################################################################################################
######1.0 INPUT DE DATOS##########################################################################
##################################################################################################

######0.1 Cargar DEM de Colombia y drenajes#######################################################

### DEM ###
dem = raster("DEM.tif")
dem.utm = spTransform(dem, CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'")) 

### Drenajes dobles y sencillos ###


sf1 <- shapefile("C:/Users/Jorge/OneDrive/TESIS MAESTRIA - HIDROECONOMICS/Shapes/Drenajes IGAC 100K/Drenajes_Dobles.shp")
sf2 <- shapefile("C:/Users/Jorge/OneDrive/TESIS MAESTRIA - HIDROECONOMICS/Shapes/Drenajes IGAC 100K/Drenajes_Sencillos.shp")
proj4string(sf1)
sf1.utm = spTransform(sf1, CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'"))
sf2.utm = spTransform(sf2, CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'"))
proj4string(dem)
proj4string(sf1.utm)
proj4string(sf2.utm)
rm(sf1)
rm(sf2)



######0.2Cargar coordenadas de los puntos de cierre de las CH#####################################

pih <- read.csv("E:/pih.csv",header=TRUE, sep=";")
pih.df <- data.frame(pih)
coordinates(pih) <- c( "Lon", "Lat" )
pih.utm = spTransform(pih, CRS(sf1))
BufferPih <- gBuffer( pih.df, width=0.1, byid=TRUE )
plot(pih.df)
plot(BufferPih, add = T )
plot(gBuffer(BufferPih, width=0.1), lwd=2)
plot(BufferPih)

######0.3 cortar Shapes Interseptooooo ###########################################################


sf1Short <- raster::intersect(sf1 , dem)


##################################################################################################

sf1.utm = spTransform(sf1, CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0"))
sf2.utm = spTransform(sf2, CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0"))

sf1l = as(sf1.utm, "SpatialLines")
sf2l = as(sf2.utm, "SpatialLines")



# write dem.utm to SAGA format
writeRaster(dem, filename = "SFdem.sgrd", format = "SAGA", overwrite = T)


# fill sinks - note that the algorithm will create negative elevations in Howe Sound
rsaga.fill.sinks(
  in.dem = "SFdem.sgrd", out.dem = "SFdemutmfilled.sgrd", 
  method = "xxl.wang.liu.2006" , minslope = 0.1,
  env = myenv
)

plot(dem)
plot(sf1, add = T)
plot(sf2, add = T, col = "blue")


# catchment outlet (point of interest, poi) 
poill = data.frame(x = -123.105792, y = 49.659664)  
coordinates(poill) = ~x + y
projection(poill) = CRS("+proj=longlat +datum=WGS84") 
poi = spTransform(poill, CRSobj = CRS("+proj=longlat +ellps=GRS80 +no_defs"))



#proj4string(dem)
#summary(dem)
#ph.dfcrs <- spTransform(dem, crs(philly))
#dem.utm = projectRaster(dem , crs = "+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0") 



shpdir = "E:/Drenajes IGAC 100K"
shps = dir(shpdir, "*.shp")
nshps = length(shps)
used.shapes = c("Drenajes_Dobles.shp", "Drenajes_Sencillos.shp")

nc = nchar(used.shapes)
layername = substr(used.shapes, 1, (nc - 4))
sf1 = readOGR(dsn = shpdir, layer = layername[1])
sf2 = readOGR(dsn = shpdir, layer = layername[2])

######0.3  Cargar coordenadas de los puntos de cierre de las CH###################################


######0.4* Revisar en mapa los resultados - PLOT PLOT PLOT #######################################

##################################################################################################
######1.0 Delimitación de cuencas ################################################################
##################################################################################################

######1.1 Construir raster del DEM en formato SAGA################################################

writeRaster( DEM COLOMBIA , filename = "SFDEMutm.sgrd", format = "SAGA", overwrite = T)

######1.1.1 Llena sumideros y cargar archivo######################################################

rsaga.fill.sinks(
  in.dem = "SFDEMutm.sgrd", 
  out.dem = "SFDEMutmfilled.sgrd", 
  method = "xxl.wang.liu.2006" , minslope = 0.1
)

fill_dem = raster("SFDEMutmfilled.sdat")
projection(fill_dem) <- CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'")
values(fill_dem) = ifelse(values(fill_dem) < 0, NA, values(fill_dem))

###### 1.2 Definir las áreas de drenaje y de la pendiente##########################################

rsaga.topdown.processing("SFdemutmfilled.sgrd", out.carea = "SFda.sgrd", env = myenv)
SFda = raster("SFda.sdat")
projection(SFda) = CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'")
plot(log(SFda))
plot(poi, add = T)
contour(fill_dem, add = T)


###### 1.3   Delimitar cuenca a partir del punto de interes ######################################

##################################################################################################
###### Busca la mayor área de drenaje a partir del punto - Buffer puede ajustarse de acuerdo #####
###### a la necesidad 50 m -                Ingresar coordenadas y el buffer                 #####
##################################################################################################

buff = raster::extract(x = SFda, y = poi, buffer = 10000, cellnumbers = TRUE)
buff.df = as.data.frame(buff)
snap_cell <- buff.df$cell[which.max(buff.df$value)]
snap_xy <- xyFromCell(SFda, snap_cell)
snap_xy = data.frame(y = snap_xy[1, 2], x = snap_xy[1, 1])
coordinates(snap_xy) = ~ x + y

##################################################################################################
###### Determina que pixeles drenan hacia el punto de interes                                #####
###### guarda la información como grid                                                       #####
##################################################################################################

rsaga.geoprocessor(
  lib = 'ta_hydrology', module = 4, env = myenv,
  param = list(TARGET_PT_X = snap_xy@coords[1],
               TARGET_PT_Y = snap_xy@coords[2],
               ELEVATION = 'SFdemutmfilled.sgrd',
               AREA = 'basin.sgrd',
               METHOD = 0)					 
)

##################################################################################################
###### Convierte a poligono                                                                  #####
##################################################################################################

rsaga.geoprocessor(
  lib = 'shapes_grid', module = 6, env = myenv,
  param = list(GRID = 'basin.sgrd',
               POLYGONS = 'basin.shp',
               CLASS_ALL = 0,
               CLASS_ID = 100,
               SPLIT = 0
  )
)					 			 


##################################################################################################
###### Lee la información como Poligonoy reproyecta                                          #####
##################################################################################################


basin.spdf = readShapeSpatial('basin.shp', proj4string = CRS("+proj=utm +zone=10 +ellps=WGS84"))


##################################################################################################
###### Convierte a lineas                                                                    #####
##################################################################################################

basin.sl = as(basin.spdf, "SpatialLines")

