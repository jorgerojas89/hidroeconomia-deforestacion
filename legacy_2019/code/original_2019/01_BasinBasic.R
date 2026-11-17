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


CRSutm <- CRS('+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0')
#####   de drenajes +proj=longlat +ellps=GRS80 +no_defs

##################################################################################################
######1.0 INPUT DE DATOS##########################################################################
##################################################################################################

######0.1 Cargar DEM de Colombia y drenajes#######################################################

### DEM ###
dem = raster("DEM.tif")

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

sf1l = as(sf1.utm, "SpatialLines")
sf2l = as(sf2.utm, "SpatialLines")

rm(sf1.utm)
rm(sf2.utm)

plot(dem)
plot(sf1l, add = T, col = "red")



######0.2Cargar coordenadas de los puntos de cierre de las CH#####################################

poill = data.frame(x = -76.86698438, y = 3.533074389)  
coordinates(poill) = ~x + y
projection(poill) = CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'") 
poi = spTransform(poill, CRSobj = CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'"))

proj4string(poi)
proj4string(poill)

# plot dem, tidbit locations and poi to check that everything looks okay
plot(dem)
plot(sf1l, add = T, col = "blue")
plot(poi, add = T, pch = 21, bg = "cyan")

########################################################################
# delineate catchment area polygon using SAGA                          #
########################################################################

# write dem.utm to SAGA format
BufferPih <- gBuffer(poi, width=1, byid=TRUE )
projection(BufferPih) = CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'")
dem.inter = intersect(dem, BufferPih)
writeRaster(dem.buff, filename = "SFdemutmBuff.sgrd", format = "SAGA", overwrite = T)

# fill sinks - note that the algorithm will create negative elevations in Howe Sound

rsaga.fill.sinks(
  in.dem = "C:/Users/Jorge/OneDrive/TESIS MAESTRIA - HIDROECONOMICS/Shapes/SFdemutmBuff.sgrd", out.dem = "SFdemfilledBuff.sgrd", 
  method = "xxl.wang.liu.2006" , minslope = 0.1,
  env = myenv
)

# read in filled dem, specify projection and convert negative values to NA
fill_dem = raster("C:/Users/Jorge/Documents/SFdemfilledBuff.sdat")
projection(fill_dem) <- CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'")
values(fill_dem) = ifelse(values(fill_dem) < 0, NA, values(fill_dem))

# determine upslope drainage areas and map
rsaga.topdown.processing("C:/Users/Jorge/Documents/SFdemfilledBuff.sdat", out.carea = "SFdaBuff.sgrd", env = myenv)
SFda = raster("C:/Users/Jorge/Documents/SFdaBuff.sdat")
projection(SFda) = CRS("+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0'")



# find maximum drainage area near the poi - assign as catchment outlet
# i'm using a buffer of 50 m, but a different size may be appropriate
# for different data sets
buff = raster::extract(x = SFda, y = poi, buffer = 0.01, cellnumbers = TRUE)
buff.df = as.data.frame(buff)
snap_cell <- buff.df$cell[which.max(buff.df$value)]
snap_xy <- xyFromCell(SFda, snap_cell)
snap_xy = data.frame(y = snap_xy[1, 2], x = snap_xy[1, 1])
coordinates(snap_xy) = ~ x + y

# determine pixels that drain into the poi - save as grid
rsaga.geoprocessor(
  lib = 'ta_hydrology', module = 4, env = myenv,
  param = list(TARGET_PT_X = snap_xy@coords[1],
               TARGET_PT_Y = snap_xy@coords[2],
               ELEVATION = 'C:/Users/Jorge/Documents/SFdemfilledBuff.sdat',
               AREA = 'basin.sgrd',
               METHOD = 0
  )					 
)
rsaga.geop
# convert grid version of catchment to a polygon
rsaga.geoprocessor(
  lib = 'shapes_grid', module = 6, env = myenv,
  param = list(GRID = 'basin.sgrd',
               POLYGONS = 'basin.shp',
               CLASS_ALL = 0,
               CLASS_ID = 100,
               SPLIT = 0
  )
)					 			 

# read in the shapefile as a spatial polygons data frame
basin.spdf = readShapeSpatial('basin.shp', proj4string = CRS("+proj=utm +zone=10 +ellps=WGS84"))

# convert the spdf to a spatial lines object 
basin.sl = as(basin.spdf, "SpatialLines")

# create full map with all elements
bb = bbox(fill_dem)
xminmax = bb[1, ]
yminmax = bb[2, ]

xmin = min(xminmax)
xmax = max(xminmax)
ymin = min(yminmax)
ymax = max(yminmax)
xsb = xmax + 500
ysb = ymin + 700

# to generate map and store as a tiff file, uncomment the following line and the last line of the script
# tiff("Figure4.tiff")
par(mar = c(1, 1, 1, 1), cex = 1.1)
plot(sf1.utm, xlim = c(xmin, xmax + 700), col = "black", axes = F)
plot(fill_dem, add = T, 
     col = gray(seq(1, 0.2, by = -0.1), alpha = 1),
     legend.mar = 5,
     legend.width = 0.6, legend.shrink = 0.4,
     legend.args = list(text = '  Elevation (m)', side = 3, font = 2, line = 1, cex = 0.8)
)

plot(sf2.utm, add = T, col = "blue")
plot(tb, add = T, pch = 21, bg = "red")
plot(ufwx, add = T, pch = 21, bg = "yellow")
plot(sap, add = T, pch = 22, bg = "yellow")
plot(basin.sl, col = "yellow", add = T) 
plot(sf1.utm, xlim = c(xmin, xmax + 5000), col = "black", add = T)

scalebar(4000, xy = c(xsb, ysb), 
         divs = 4,
         label = c(0, 2, 4), below = "km",
         type = "bar"
)

north.arrow(xb = xmax + 2500, yb = ymin + 3500, len = 300, col = "lightgray")

legend("topright", bty = "n",
       pch = c(22, 21, 21), 
       legend = c("YOW", expression(italic(T[w])), "UF Wx"),
       pt.bg = c("yellow", "red", "yellow")
)

text(x = xmin + 2500, y = ymin + 5500, 
     labels = expression(italic("Howe Sound")),
     srt = 20, cex = 0.8
)

# dev.off()