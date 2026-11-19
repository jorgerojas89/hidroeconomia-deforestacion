"""T4 paso 1: exporta la capa atch_unidad a shapefile zip en EPSG:4326 para subirla a Earth Engine.
Correr desde 03_tesis:  python3 03_codigo/02_earth_engine/exportar_cuencas_ee.py
Se exportan las 34 unidades con ATCH (no solo las 26 de la muestra): la marca de muestra
se aplica después, en el panel (T6), así una ampliación de la muestra no obliga a volver a Earth Engine
salvo para unidades nuevas."""
import geopandas as gpd, zipfile, os, tempfile
from shapely.validation import make_valid

SRC = "02_datos/cuencas_igac/cuencas_atch_igac.gpkg"
OUT = "02_datos/earth_engine"
os.makedirs(OUT, exist_ok=True)

u = gpd.read_file(SRC, layer="atch_unidad")
u = u.to_crs(4326)
u["geometry"] = u.geometry.apply(lambda g: g if g.is_valid else make_valid(g))
u["geometry"] = u.geometry.apply(lambda g: g.buffer(0) if g.geom_type not in ("Polygon", "MultiPolygon") else g)
assert u.is_valid.all(), "geometrías inválidas"
out = gpd.GeoDataFrame({
    "unidad": u["unidad"],
    "codigo_xm": u["codigo_xm"],
    "atch_ha": u["area_union_ha"].round(2),
    "n_proy": u["n_proyectos"],
}, geometry=u.geometry, crs=4326)

tmp = os.path.join(tempfile.mkdtemp(), "atch_unidad_ee")   # el .shp suelto queda fuera de OneDrive
out.to_file(tmp + ".shp", encoding="utf-8")
zpath = os.path.join(OUT, "atch_unidad_ee.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        z.write(tmp + ext, "atch_unidad_ee" + ext)
print(len(out), "unidades ->", zpath, round(os.path.getsize(zpath)/1e6, 2), "MB")
print(out.drop(columns="geometry").to_string())
