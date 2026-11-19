"""Extrae la cuenca hidrográfica total (ATCH) de cada proyecto IGAC.

Entradas (relativas a 03_tesis/02_datos):
  IGAC_cuencas/anexos_oficios_TSE/<Proyecto>/shp_<Proyecto>/<...>_ATCH.shp
  IGAC_certificados/*.pdf            (radicado y área ATCH declarada)
  tabla_maestra/tabla_maestra.csv    (unidad, muestra_principal, sistema hídrico)

Salidas en 02_datos/cuencas_igac/:
  cuencas_atch_igac.gpkg  capa 'atch_proyecto' (una fila por certificado)
                          capa 'atch_unidad'   (unión por unidad XM)
  cuencas_atch_igac.csv   tabla de áreas y validación (sin geometría)

Regla: se toma solo el archivo cuyo nombre termina en '_ATCH.shp'. Se descartan
los cruces (_Mpio, _x_ATP, ATIxATCH, etc.). Chivor trae además 'ATCH_Rnegro.shp',
que no se usa (ver nota en la salida).
Correr con: python3 03_codigo/01_cuencas/extraer_atch_igac.py  (desde 03_tesis)
"""
import glob, os, re, subprocess, unicodedata
import geopandas as gpd, pandas as pd

D = '02_datos'
OUT = os.path.join(D, 'cuencas_igac'); os.makedirs(OUT, exist_ok=True)

def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

def num(s):  # "269.325,76227" -> float
    return float(s.replace('.', '').replace(',', '.'))

# 1. Certificados: radicado, proyecto (asunto) y área ATCH declarada
certs = []
for pdf in sorted(glob.glob(os.path.join(D, 'IGAC_certificados', '*.pdf'))):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    rad = re.search(r'Radicado N°:\s*(\S+)', txt).group(1)
    fecha = re.search(r'Fecha:\s*(\d{2}-\d{2}-\d{4})', txt)
    proy = re.search(r'Proyecto\s+(.+?)\.\s*\n', txt.split('ASUNTO')[1], re.S)
    proy = ' '.join(proy.group(1).split()) if proy else None
    # primer número con formato de hectáreas después de la etiqueta ATCH
    blk = txt[txt.find('\nATCH'):]
    m = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{5})', blk)
    anexos = re.findall(r'\d+\.\s+(\S*ATCH\S*\.shp)', txt)
    certs.append(dict(radicado=rad, fecha_cert=fecha.group(1) if fecha else None,
                      proyecto_cert=proy, atch_cert_ha=num(m.group(1)) if m else None,
                      archivo_pdf=os.path.basename(pdf), anexos_atch=';'.join(anexos)))
certs = pd.DataFrame(certs)

# 2. Capas ATCH
filas = []
for shp in sorted(glob.glob(os.path.join(D, 'IGAC_cuencas', 'anexos_oficios_TSE', '*', '*', '*.shp'))):
    nombre = os.path.basename(shp)
    if not re.search(r'_ATCH\.shp$', nombre, re.I) or re.search(r'mpio', nombre, re.I):
        continue
    carpeta = shp.split(os.sep)[-3]
    g = gpd.read_file(shp).to_crs(9377)
    attr = next((c for c in ['haIGAC', 'Ha', 'area_ha', 'Area'] if c in g.columns), None)
    from shapely import force_2d, make_valid
    geom = force_2d(g.union_all())
    reparada = not geom.is_valid
    if reparada:  # auto-intersecciones puntuales del original; no cambia el área
        geom = make_valid(geom)
    filas.append(dict(carpeta=carpeta, archivo_shp=os.path.basename(shp), n_poligonos_origen=len(g),
                      ha_atributo=float(pd.to_numeric(g[attr].astype(str).str.replace(',', '.'), errors='coerce').sum()) if attr else None,
                      atch_shape_ha=geom.area / 1e4, geom_reparada=reparada, geometry=geom))
atch = gpd.GeoDataFrame(filas, crs=9377)

# 3. Enlace carpeta -> certificado (por el nombre del archivo en la lista de anexos)
def cert_de(row):
    for _, c in certs.iterrows():
        if row.archivo_shp in c.anexos_atch.split(';'):
            return c.radicado
    return None
atch['radicado'] = atch.apply(cert_de, axis=1)
atch = atch.merge(certs, on='radicado', how='left')
atch['dif_pct_shape_vs_cert'] = 100 * (atch.atch_shape_ha / atch.atch_cert_ha - 1)

# 4. Tabla maestra: unidad, muestra, sistema
tm = pd.read_csv(os.path.join(D, 'tabla_maestra', 'tabla_maestra.csv'))
tm = tm[tm.igac_radicados.notna()]
r2u = {}
for _, t in tm.iterrows():
    for r in str(t.igac_radicados).split(';'):
        r2u[r.strip()] = t
for c in ['unidad', 'codigo_xm', 'muestra_principal', 'sistema_hidrico_propuesto', 'tipo_propuesto', 'acueducto']:
    atch[c] = atch.radicado.map(lambda r: r2u[r][c] if r in r2u else None)
atch['muestra_principal'] = atch.muestra_principal.fillna(0).astype(int)
atch['nota'] = ''
rn = gpd.read_file(glob.glob(os.path.join(D, 'IGAC_cuencas', 'anexos_oficios_TSE', 'Chivor', '*', 'ATCH_Rnegro.shp'))[0]).to_crs(9377)
atch.loc[atch.carpeta == 'Chivor', 'nota'] = (f'Certificado trae también ATCH_Rnegro.shp ({rn.union_all().area/1e4:,.0f} ha), '
                                              'no usado: el área declarada coincide con Chivor_ATCH.shp')
# Proyectos con la misma ATCH (diferencia de área < 0,01 % y geometrías casi iguales)
iguales = []
for i, a in atch.iterrows():
    otros = [b.carpeta for j, b in atch.iterrows() if j != i
             and a.geometry.symmetric_difference(b.geometry).area < 1e-4 * a.geometry.area]
    iguales.append('; '.join(otros))
atch['misma_atch_que'] = iguales

cols = ['unidad', 'codigo_xm', 'carpeta', 'proyecto_cert', 'radicado', 'fecha_cert', 'muestra_principal',
        'sistema_hidrico_propuesto', 'tipo_propuesto', 'acueducto', 'atch_cert_ha', 'atch_shape_ha',
        'dif_pct_shape_vs_cert', 'misma_atch_que', 'geom_reparada', 'ha_atributo', 'n_poligonos_origen', 'archivo_shp', 'archivo_pdf', 'nota']
atch = atch[cols + ['geometry']].sort_values(['muestra_principal', 'unidad'], ascending=[False, True])

# 5. Unidad XM (GUATRON, PAJARITO: unión de sus proyectos)
u = atch[atch.unidad.notna()].dissolve(by='unidad', aggfunc={
    'codigo_xm': 'first', 'radicado': lambda s: '; '.join(s), 'carpeta': lambda s: '; '.join(s),
    'muestra_principal': 'max', 'sistema_hidrico_propuesto': 'first', 'tipo_propuesto': 'first',
    'acueducto': 'first', 'atch_cert_ha': 'sum'}).reset_index()
u = u.rename(columns={'atch_cert_ha': 'suma_atch_cert_ha'})
u['area_union_ha'] = u.geometry.area / 1e4
u['n_proyectos'] = u.radicado.str.count(';') + 1

# SQLite no escribe bien en carpetas sincronizadas (OneDrive): se arma en tmp y se copia
import shutil, tempfile
tmp = os.path.join(tempfile.mkdtemp(), 'cuencas_atch_igac.gpkg')
atch.to_file(tmp, layer='atch_proyecto', driver='GPKG')
u.to_file(tmp, layer='atch_unidad', driver='GPKG')
shutil.copyfile(tmp, os.path.join(OUT, 'cuencas_atch_igac.gpkg'))
atch.drop(columns='geometry').to_csv(os.path.join(OUT, 'cuencas_atch_igac.csv'), index=False)
u.drop(columns='geometry').to_csv(os.path.join(OUT, 'cuencas_atch_unidad.csv'), index=False)
print(atch.drop(columns='geometry').to_string())
print(u.drop(columns='geometry').to_string())
