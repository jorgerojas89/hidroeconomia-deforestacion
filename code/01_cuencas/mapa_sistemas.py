"""Mapa de las ATCH de la muestra principal coloreadas por sistema hídrico (variante A y B)."""
import os, shutil, tempfile
import geopandas as gpd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, pandas as pd
OUT = '02_datos/cuencas_igac'
tmp = os.path.join(tempfile.mkdtemp(), 'c.gpkg'); shutil.copyfile(f'{OUT}/cuencas_atch_igac.gpkg', tmp)
u = gpd.read_file(tmp, layer='atch_unidad'); u = u[u.muestra_principal == 1]
s = pd.read_csv(f'{OUT}/sistemas_hidricos.csv')
u = u.merge(s[['unidad', 'sistema_geom_A', 'sistema_geom_B']], on='unidad')
u['ha'] = u.area; u = u.sort_values('ha', ascending=False)   # grandes abajo
fig, axs = plt.subplots(1, 2, figsize=(16, 10))
for ax, col, tit in [(axs[0], 'sistema_geom_A', f'A: cuencas anidadas unidas ({u.sistema_geom_A.nunique()} sistemas)'),
                     (axs[1], 'sistema_geom_B', f'B: Ituango no une sistemas ({u.sistema_geom_B.nunique()})')]:
    u.plot(column=col, ax=ax, cmap='tab20', alpha=0.55, edgecolor='k', linewidth=0.4, legend=True,
           legend_kwds=dict(loc='lower left', fontsize=7, title='Sistema'))
    for _, r in u.iterrows():
        p = r.geometry.representative_point()
        ax.annotate(r.unidad.title(), (p.x, p.y), fontsize=6, ha='center')
    ax.set_title(tit); ax.set_axis_off()
fig.suptitle(f'Cuencas ATCH del IGAC, muestra principal ({len(u)} unidades). EPSG:9377', fontsize=12)
plt.tight_layout(); plt.savefig(f'{OUT}/mapa_sistemas_hidricos.png', dpi=130)
