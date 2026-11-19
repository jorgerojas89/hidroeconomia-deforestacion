"""T3: sistemas hídricos, traslapes y comparaciones de las cuencas ATCH del IGAC.

Requiere haber corrido extraer_atch_igac.py. Correr desde 03_tesis:
    python3 03_codigo/01_cuencas/analizar_cuencas.py

Salidas en 02_datos/cuencas_igac/:
  sistemas_hidricos.csv      sistema hídrico por unidad, derivado de la geometría
  traslapes_unidades.csv     hectáreas compartidas entre pares de unidades
  hectareas_por_unidad.csv   área propia vs. compartida (para valorar sin doble conteo)
  comparacion_2019.csv       área ATCH vs. área de cuenca usada en la tesis de 2019
  comparacion_version_2025.csv  ATCH 2026 vs. polígonos de 02_datos/cuencas_prueba (oct-2025)
"""
import glob, itertools, os, re, shutil, tempfile, unicodedata
import geopandas as gpd, networkx as nx, pandas as pd

D = '02_datos'; OUT = os.path.join(D, 'cuencas_igac')
UMBRAL_TRASLAPE = 0.05   # dos cuencas se conectan si comparten > 5 % del área de la menor
UMBRAL_DENTRO = 0.95     # A está dentro de B si > 95 % de A cae en B
CUENCAS_MADRE = ['ITUANGO']  # variante B: cuenca del cauce principal que no une sistemas
UMBRAL_DIF = 0.10        # diferencias de área > 10 % se marcan

tmp = os.path.join(tempfile.mkdtemp(), 'c.gpkg')
shutil.copyfile(os.path.join(OUT, 'cuencas_atch_igac.gpkg'), tmp)
u = gpd.read_file(tmp, layer='atch_unidad')
u['ha'] = u.area / 1e4
u = u.set_index('unidad')
M = set(u.index[u.muestra_principal == 1])

# ---------- 1 y 2. Traslapes entre pares ----------
pares = []
for a, b in itertools.combinations(u.index, 2):
    x = u.geometry[a].intersection(u.geometry[b]).area / 1e4
    if x <= 0:
        continue
    fa, fb = x / u.ha[a], x / u.ha[b]
    if min(fa, fb) > 0.99 and max(fa, fb) > 0.99:
        rel = 'misma cuenca'
    elif fa > UMBRAL_DENTRO:
        rel = f'{a} dentro de {b}'
    elif fb > UMBRAL_DENTRO:
        rel = f'{b} dentro de {a}'
    elif max(fa, fb) > UMBRAL_TRASLAPE:
        rel = 'traslape parcial'
    else:
        rel = 'borde (despreciable)'
    pares.append(dict(unidad_a=a, unidad_b=b, muestra_a=int(a in M), muestra_b=int(b in M),
                      ha_compartidas=x, frac_de_a=fa, frac_de_b=fb, relacion=rel))
pares = pd.DataFrame(pares).sort_values('ha_compartidas', ascending=False)
pares.round(4).to_csv(os.path.join(OUT, 'traslapes_unidades.csv'), index=False)

# ---------- 1. Sistemas hídricos (componentes conectados, solo muestra principal) ----------
def componentes(excluir_madre):
    G = nx.Graph(); G.add_nodes_from(M)
    for _, p in pares.iterrows():
        if p.muestra_a and p.muestra_b and max(p.frac_de_a, p.frac_de_b) > UMBRAL_TRASLAPE:
            if excluir_madre and (p.unidad_a in CUENCAS_MADRE or p.unidad_b in CUENCAS_MADRE):
                continue
            G.add_edge(p.unidad_a, p.unidad_b)
    nombre = {}
    for comp in nx.connected_components(G):
        salida = max(comp, key=lambda n: (round(u.ha[n]), u.tipo_propuesto[n] == 'embalse', n))  # la más grande (la de más abajo); empate: embalse
        for n in comp:
            nombre[n] = salida
    return nombre

sA, sB = componentes(False), componentes(True)
def contenedora(n):  # la cuenca más pequeña de la muestra que contiene a n
    c = [(u.ha[b], b) for _, p in pares.iterrows() for a, b in [(p.unidad_a, p.unidad_b), (p.unidad_b, p.unidad_a)]
         if a == n and b in M and p.relacion == f'{n} dentro de {b}']
    return min(c)[1] if c else ''
sis = pd.DataFrame({'unidad': sorted(M)})
sis['ha_atch'] = sis.unidad.map(u.ha)
sis['tipo'] = sis.unidad.map(u.tipo_propuesto)
sis['sistema_geom_A'] = sis.unidad.map(sA)
sis['sistema_geom_B'] = sis.unidad.map(sB)
sis['sistema_hidrico_propuesto'] = sis.unidad.map(u.sistema_hidrico_propuesto)
sis['dentro_de'] = sis.unidad.map(contenedora)
sis = sis.sort_values(['sistema_geom_A', 'ha_atch'], ascending=[True, False])
sis.round(2).to_csv(os.path.join(OUT, 'sistemas_hidricos.csv'), index=False)

# ---------- 2. Hectáreas propias y compartidas (muestra principal) ----------
from shapely.ops import unary_union
hu = []
for n in sorted(M):
    otras = unary_union([u.geometry[m] for m in M if m != n])
    comp = u.geometry[n].intersection(otras).area / 1e4
    hu.append(dict(unidad=n, ha_atch=u.ha[n], ha_compartidas_con_otras=comp,
                   ha_exclusivas=u.ha[n] - comp, frac_compartida=comp / u.ha[n]))
hu = pd.DataFrame(hu)
union = unary_union([u.geometry[m] for m in M]).area / 1e4
hu.loc[len(hu)] = dict(unidad='TOTAL (union, sin doble conteo)', ha_atch=union)
hu.loc[len(hu)] = dict(unidad='TOTAL (suma simple)', ha_atch=sum(u.ha[m] for m in M))
hu.round(4).to_csv(os.path.join(OUT, 'hectareas_por_unidad.csv'), index=False)

# ---------- 3. Comparación con 2019 ----------
tm = pd.read_csv(os.path.join(D, 'tabla_maestra', 'tabla_maestra.csv')).set_index('unidad')
c19 = tm[tm.area_cuenca_2019_ha.notna() & tm.index.isin(u.index)][['ids_2019', 'area_cuenca_2019_ha']].copy()
c19['ha_atch_2026'] = c19.index.map(u.ha)
c19['muestra_principal'] = c19.index.map(lambda n: int(n in M))
c19['razon_atch_sobre_2019'] = c19.ha_atch_2026 / c19.area_cuenca_2019_ha
c19['dif_pct'] = 100 * (c19.razon_atch_sobre_2019 - 1)
c19['marca'] = (c19.dif_pct.abs() > 100 * UMBRAL_DIF).map({True: 'dif > 10 %', False: ''})
# Hipótesis: en 2019 el área = n.º de celdas x 4,34 ha, pero las celdas eran de 7,5" (~5,35 ha).
# Razón esperada ATCH/2019 si la delimitación fuera la misma: área real de la celda / 4,34.
import numpy as np
lat = u.to_crs(9377).geometry.centroid.to_crs(4326).y
lado = 7.5 / 3600 * 111320
c19['razon_esperada_celda'] = [lado ** 2 * np.cos(np.radians(lat[n])) / 1e4 / 4.34 for n in c19.index]
c19['diagnostico'] = np.where((c19.razon_atch_sobre_2019 / c19.razon_esperada_celda - 1).abs() <= 0.05,
                              'misma cuenca; 2019 subestima el área por la celda',
                              'delimitación distinta a la oficial')
c19 = c19.sort_values('razon_atch_sobre_2019')
c19.round(3).to_csv(os.path.join(OUT, 'comparacion_2019.csv'))

# ---------- 4. Control: versión anterior (02_datos/cuencas_prueba, oct-2025) ----------
MAPA = {'Alto_Tulua': 'ALTO TULUA', 'Amaime': 'AMAIME', 'Amoya': 'AMOYA LA ESPERANZA', 'Bajo_Anchicaya': 'ALBAN',
        'Bajo_Tulua': 'BAJO TULUA', 'Betania': 'BETANIA', 'Calderas': 'CALDERAS', 'Calima': 'CALIMA',
        'Caracoli': 'CARACOLI', 'Guatape': 'GUATAPE', 'Guatron': 'GUATRON', 'Guavio': 'GUAVIO',
        'Herradura': 'LA HERRADURA', 'Ituango': 'ITUANGO', 'Jaguas': 'JAGUAS', 'La_Vuelta': 'LA VUELTA',
        'Miel_I': 'MIEL I', 'Pajarito_II': 'PAJARITO', 'Playas': 'PLAYAS', 'Porce_II': 'PORCE II',
        'Porce_III': 'PORCE III', 'Prado': 'PRADO', 'Quimbo': 'EL QUIMBO', 'RioFrio_1_Celsia': 'RIO FRIO I',
        'RioFrio_2_Celsia': 'RIO FRIO II', 'Riofrio': 'RIOFRIO (TAMESIS)', 'Riogrande': 'RIOGRANDE I',
        'Rumor': 'RUMOR', 'Salvajina': 'SALVAJINA', 'San_Carlos': 'SAN CARLOS', 'San_Francisco': 'SAN FRANCISCO',
        'Sogamoso': 'SOGAMOSO', 'Sonson': 'SONSON', 'Sueva_I': 'SUEVA I', 'Sueva_II': 'SUEVA 2',
        'Tasajera': 'LA TASAJERA', 'rio_Bobo': 'RIO BOBO', 'rio_Mayo': 'RIO MAYO'}
v = []
for f in sorted(glob.glob(os.path.join(D, 'cuencas_prueba', 'Cuenca_*.shp'))):
    nom = os.path.basename(f)[7:-4]
    g = gpd.read_file(f).to_crs(9377).union_all()
    un = MAPA.get(nom, '')
    fila = dict(archivo=os.path.basename(f), unidad=un, ha_version_2025=g.area / 1e4,
                ha_2019=tm.area_cuenca_2019_ha.get(un) if un else None)
    if un in u.index:
        a = u.geometry[un]
        fila.update(ha_atch_2026=u.ha[un], iou=a.intersection(g).area / a.union(g).area,
                    dif_pct=100 * (g.area / a.area - 1))
    v.append(fila)
v = pd.DataFrame(v)
v['estado'] = v.apply(lambda r: ('igual' if r.iou > 0.99 else 'difiere') if pd.notna(r.get('iou')) else
                      ('sin ATCH 2026' if r.unidad else 'sin unidad en la tabla maestra'), axis=1)
v.round(3).to_csv(os.path.join(OUT, 'comparacion_version_2025.csv'), index=False)

pd.set_option('display.width', 250)
print(sis.round(0).to_string(index=False)); print()
print('Sistemas A:', sis.sistema_geom_A.nunique(), ' B:', sis.sistema_geom_B.nunique(),
      ' propuestos:', sis.sistema_hidrico_propuesto.nunique()); print()
print(pares[pares.relacion != 'borde (despreciable)'].round(3).to_string(index=False)); print()
print(hu.round(0).to_string(index=False)); print()
print(c19.round(2).to_string()); print()
print(v.round(3).to_string(index=False))
