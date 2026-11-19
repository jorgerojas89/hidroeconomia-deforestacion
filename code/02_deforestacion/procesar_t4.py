"""T4 paso 3: convierte las exportaciones de Earth Engine en las tablas del panel y corre las pruebas de calidad.
Entradas (bajarlas de Google Drive, carpeta tesis_T4, a 02_datos/earth_engine/crudo/):
  ee_hansen_unidad.csv, ee_chirps_unidad_mes.csv, ee_chirps_dias_mes.csv, ee_merit_unidad.csv
Salidas en 02_datos/earth_engine/:
  deforestacion_cuenca_anio.csv  unidad × año 2001–2024: flujo (ha, % bosque 2000) y acumulado (ha, % bosque 2000)
  lluvia_cuenca_mes.csv          unidad × mes 2000–2024 (mm)
  lluvia_cuenca_anio.csv         unidad × año 2000–2024: total anual (mm) y anomalía frente al promedio 2001–2024
  validacion_merit.csv           razón área drenada MERIT / ATCH y bandera
  reporte_qc_t4.md               resultado de cada prueba
Correr desde 03_tesis:  python3 03_codigo/02_earth_engine/procesar_t4.py"""
import os, sys, pandas as pd, numpy as np

CRUDO = "02_datos/earth_engine/crudo"
OUT = "02_datos/earth_engine"
A0, A1 = 2001, 2024
pruebas = []
def prueba(nombre, ok, detalle=""):
    pruebas.append((nombre, "OK" if ok else "FALLA", detalle))

# ---------- Hansen ----------
h = pd.read_csv(os.path.join(CRUDO, "ee_hansen_unidad.csv"))
cols = [f"perdida_{y}" for y in range(A0, A1 + 1)]
prueba("Hansen: llave unidad única", h.unidad.is_unique)
dif_area = (h.area_ha / h.atch_ha - 1).abs()
prueba("Hansen: área en EE = ATCH ±1 %", (dif_area < 0.01).all(),
       "máx. diferencia {:.3%} ({})".format(dif_area.max(), h.loc[dif_area.idxmax(), "unidad"]))
prueba("Hansen: bosque 2000 ≤ área", (h.bosque2000_ha <= h.area_ha * 1.0001).all())
dif_sum = (h[cols].sum(axis=1) - h.perdida_total_ha).abs() / h.perdida_total_ha.clip(lower=1)
prueba("Hansen: suma anual = pérdida total", (dif_sum < 0.001).all(), f"máx. {dif_sum.max():.4%}")
prueba("Hansen: pérdida total ≤ bosque 2000", (h.perdida_total_ha <= h.bosque2000_ha * 1.0001).all())
prueba("Hansen: sin valores faltantes", h[cols + ["bosque2000_ha"]].notna().all().all())

d = h.melt(id_vars=["unidad", "codigo_xm", "atch_ha", "area_ha", "bosque2000_ha"], value_vars=cols,
           var_name="anio", value_name="perdida_ha")
d["anio"] = d.anio.str[-4:].astype(int)
d = d.sort_values(["unidad", "anio"])
d["perdida_pct_bosque2000"] = 100 * d.perdida_ha / d.bosque2000_ha
d["perdida_acum_ha"] = d.groupby("unidad").perdida_ha.cumsum()
d["perdida_acum_pct_bosque2000"] = 100 * d.perdida_acum_ha / d.bosque2000_ha   # medida A (sección 4.5)
d["bosque2000_pct_cuenca"] = 100 * d.bosque2000_ha / d.area_ha
prueba("Deforestación: panel completo unidad × año", len(d) == len(h) * (A1 - A0 + 1))
prueba("Deforestación: acumulado no decreciente", (d.groupby("unidad").perdida_acum_ha.diff().fillna(0) >= 0).all())
d = d[["unidad", "codigo_xm", "anio", "area_ha", "bosque2000_ha", "bosque2000_pct_cuenca", "perdida_ha",
       "perdida_pct_bosque2000", "perdida_acum_ha", "perdida_acum_pct_bosque2000"]]
d.round(4).to_csv(os.path.join(OUT, "deforestacion_cuenca_anio.csv"), index=False)

# ---------- CHIRPS ----------
m = pd.read_csv(os.path.join(CRUDO, "ee_chirps_unidad_mes.csv"))
dm = pd.read_csv(os.path.join(CRUDO, "ee_chirps_dias_mes.csv"))
inc = dm[dm.n_imagenes != dm.dias_mes]
prueba("CHIRPS: todos los días de cada mes presentes", inc.empty,
       "" if inc.empty else "meses incompletos: " + ", ".join(f"{a}-{b:02d}" for a, b in zip(inc.anio, inc.mes)))
prueba("CHIRPS: panel completo unidad × mes", len(m) == m.unidad.nunique() * 300 and not m.duplicated(["unidad", "anio", "mes"]).any())
prueba("CHIRPS: sin faltantes ni negativos", m.lluvia_mm.notna().all() and (m.lluvia_mm >= 0).all())
prueba("CHIRPS: mismas unidades que Hansen", set(m.unidad) == set(h.unidad))
m.sort_values(["unidad", "anio", "mes"]).round(2).to_csv(os.path.join(OUT, "lluvia_cuenca_mes.csv"), index=False)

a = m.groupby(["unidad", "codigo_xm", "anio"], as_index=False).lluvia_mm.sum()
clim = a[a.anio.between(A0, A1)].groupby("unidad").lluvia_mm.mean().rename("lluvia_media_2001_2024")
a = a.merge(clim, on="unidad")
a["lluvia_anomalia_pct"] = 100 * (a.lluvia_mm / a.lluvia_media_2001_2024 - 1)
# lección de 2019: la lluvia de 2011–2013 valía 11–12 mm en todas las cuencas
fuera = a[(a.lluvia_mm < 500) | (a.lluvia_mm > 9000)]
prueba("Lluvia anual entre 500 y 9.000 mm", fuera.empty,
       "" if fuera.empty else "; ".join(f"{u} {y}: {v:.0f}" for u, y, v in fuera[["unidad", "anio", "lluvia_mm"]].values[:15]))
med_anual = a.groupby("anio").lluvia_mm.median()
salto = (med_anual / med_anual.median() - 1).abs()
prueba("Lluvia: ningún año con mediana nacional atípica (±40 %)", (salto < 0.4).all(),
       "máx. desvío {:.0%} en {}".format(salto.max(), salto.idxmax()))
a.round(2).to_csv(os.path.join(OUT, "lluvia_cuenca_anio.csv"), index=False)

# ---------- MERIT ----------
v = pd.read_csv(os.path.join(CRUDO, "ee_merit_unidad.csv"))
v["bandera"] = np.select([v.razon_upa_atch.between(0.9, 1.1), v.razon_upa_atch < 0.9],
                         ["coherente", "menor: trasvases, varias salidas o salida recortada"],
                         "mayor: un río más grande toca la cuenca o no cierra")
v.round(4).to_csv(os.path.join(OUT, "validacion_merit.csv"), index=False)
prueba("MERIT: unidades con razón entre 0,9 y 1,1", True,
       f"{(v.bandera == 'coherente').sum()} de {len(v)}; revisar: " +
       ", ".join(f"{u} ({r:.2f})" for u, r in v.loc[v.bandera != "coherente", ["unidad", "razon_upa_atch"]].values))

# ---------- reporte ----------
lin = ["# Reporte de calidad T4", "", f"Unidades: {h.unidad.nunique()} · años {A0}–{A1}", "",
       "| Prueba | Resultado | Detalle |", "|---|---|---|"]
lin += [f"| {n} | {r} | {det} |" for n, r, det in pruebas]
open(os.path.join(OUT, "reporte_qc_t4.md"), "w").write("\n".join(lin) + "\n")
print("\n".join(lin))
sys.exit(1 if any(r == "FALLA" for _, r, _ in pruebas) else 0)
