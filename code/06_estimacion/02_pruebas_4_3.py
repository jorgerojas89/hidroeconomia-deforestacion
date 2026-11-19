"""
T7 · 02 · Pruebas de la sección 4.3 (puntos 2 a 8; el 1 es el modelo principal y el 9 va en 03).

Todas usan la especificación principal (efectos fijos de unidad y año, lluvia, trasvases de Miel I,
errores por sistema A con WCR de Webb) salvo lo que la prueba cambia. Definiciones fijadas al escribir
este script, antes de ver resultados:

 2 Rezagos: D_t, D_t-1, D_t-2, D_t-3 y sus interacciones con embalse; muestra con los 3 rezagos.
   Se reportan los cuatro b1 y la suma (efecto acumulado de 0 a 3 años) en filo y en embalse.
 3 Época seca: panel mensual, FC del mes; lluvia del mes (cientos de mm); efectos fijos unidad × mes
   calendario y año × mes. Muestras: época seca propia (principal), dic–mar (robustez), meses no
   secos y todos. Además un modelo conjunto con D × seca para probar si el efecto en filo es mayor en
   los meses secos. La deforestación es la del año (dato anual).
 4 Placebo: adelanto t+1 (pierde 2024) y adelantos t+1 a t+3 (pierde 2022–2024), con D_t en el modelo.
   Se reporta cada adelanto en filo, su suma y la Wald conjunta.
 5 Sin años de El Niño: excluye 2009–2010, 2015–2016 y 2023–2024.
 6 Caudales: variable dependiente cv_diario (principal) y q7min_rel (segunda), muestra de T6 (unidades
   con serie de XM, año completo). Forma principal sin interacción: el aporte es caudal natural del río,
   aguas arriba del embalse, y el mecanismo es el mismo en los dos tipos. Se reporta también con la
   interacción y sin los años del hueco del Chinchiná.
 7 Fuente alterna SMByC: pendiente (sin datos).
 8 Muestra: sin FC > 1; sin años con meses sin registro; con años parciales (FC sobre horas en
   operación); sin Miel I 2001–2013; solo cuencas no anidadas en otra de la muestra (`dentro_de`
   vacío); centrales en cascada agrupadas por sistema A (generación y capacidad sumadas; deforestación
   y lluvia de la cuenca mayor del sistema; embalse = 1 si más de la mitad de la capacidad-año del
   sistema es de embalse); regulación continua (D × ln(1 + días de regulación) en lugar de D × embalse,
   sin Ínsula).

Salidas en 07_salidas/tablas/: t7_02_<prueba>.csv/.md y t7_02_resumen_pruebas.csv/.md
"""
import numpy as np
import pandas as pd

from t7_comun import (CONTROLES, CONTROLES_MES, ESPERADO, FE_MENSUAL, MEDIDAS, cargar_anual,
                      cargar_mensual, estimar, guardar, muestras_anuales, muestras_mensuales,
                      pruebas_basicas)

a, mm = cargar_anual(), cargar_mensual()
MA, MM = muestras_anuales(a), muestras_mensuales(mm)
COLS = ["prueba", "variante", "medida", "termino", "estimado", "ee", "p_conv", "p_wcb", "N", "unidades", "G",
        "omitidos", "nota"]
todas = []


def correr(nombre, filas, titulo, nota):
    df = pd.DataFrame(filas)
    df["prueba"] = nombre
    guardar(df, f"t7_02_{nombre}", titulo, nota, [c for c in COLS if c in df])
    todas.append(df)
    print(f"\n== {nombre}\n", df[[c for c in COLS if c in df]].round(4).to_string())


def principal_en(df, mask, variante, y="fc_pp"):
    filas = []
    for m in MEDIDAS:
        filas += estimar(df[mask], y, [f"D_{m}", f"DE_{m}"] + CONTROLES, pruebas_basicas(m),
                         etiqueta={"medida": m, "variante": variante})
    return filas


# 2. Rezagos ----------------------------------------------------------------------------
f = []
for m in MEDIDAS:
    mask = MA["rezagos_acum"] if m == "acum_pct" else MA["rezagos_flujo"]
    s = ["", "_l1", "_l2", "_l3"]
    regs = [f"D_{m}{k}" for k in s] + [f"DE_{m}{k}" for k in s] + CONTROLES
    pr = {f"b1 {k or '_t'}": {f"D_{m}{k}": 1.0} for k in s}
    pr["suma b1 t…t-3 (filo)"] = {f"D_{m}{k}": 1.0 for k in s}
    pr["suma b1+b2 t…t-3 (embalse)"] = {**{f"D_{m}{k}": 1.0 for k in s}, **{f"DE_{m}{k}": 1.0 for k in s}}
    f += estimar(a[mask], "fc_pp", regs, pr, etiqueta={"medida": m, "variante": "rezagos 0–3"},
                 conjuntas={"Wald b1 t…t-3 = 0 (filo)": [f"D_{m}{k}" for k in s]})
correr("2_rezagos", f, "T7 · 4.3.2 Rezagos", "D del año y de 1 a 3 años atrás, con interacción con embalse. "
       "Muestra con los 3 rezagos (pierde 2001–2003).")

# 3. Época seca (mensual) ---------------------------------------------------------------
f = []
for var, mk in [("seca propia (principal)", "mensual_seca"), ("dic–mar (robustez)", "mensual_dic_mar"),
                ("meses no secos", "mensual_no_seca"), ("todos los meses", "mensual_todos"),
                ("todos, sin meses sin registro", "mensual_sin_meses_sin_registro")]:
    for m in MEDIDAS:
        f += estimar(mm[MM[mk]], "fc_pp", [f"D_{m}", f"DE_{m}"] + CONTROLES_MES, pruebas_basicas(m),
                     fe=FE_MENSUAL, etiqueta={"medida": m, "variante": var})
mt = mm[MM["mensual_todos"]].copy()
mt["seca"] = mt["seca_principal"]
mt["lluvia_mes_seca"] = mt["lluvia_mes"] * mt["seca"]
for m in MEDIDAS:
    mt[f"D_{m}_seca"] = mt[f"D_{m}"] * mt["seca"]
    mt[f"DE_{m}_seca"] = mt[f"DE_{m}"] * mt["seca"]
    regs = [f"D_{m}", f"D_{m}_seca", f"DE_{m}", f"DE_{m}_seca", "lluvia_mes_seca"] + CONTROLES_MES
    pr = {"b1 meses no secos (filo)": {f"D_{m}": 1.0},
          "diferencia seca − no seca (filo)": {f"D_{m}_seca": 1.0},
          "b1 meses secos (filo)": {f"D_{m}": 1.0, f"D_{m}_seca": 1.0},
          "diferencia seca − no seca (embalse)": {f"D_{m}_seca": 1.0, f"DE_{m}_seca": 1.0}}
    f += estimar(mt, "fc_pp", regs, pr, fe=FE_MENSUAL, etiqueta={"medida": m, "variante": "conjunto con D × seca"})
correr("3_epoca_seca", f, "T7 · 4.3.3 Época seca (panel mensual)",
       "FC mensual en pp; lluvia del mes en cientos de mm; efectos fijos unidad × mes calendario y año × mes; "
       "errores por sistema A con WCR. Época seca principal: 4 meses más secos de cada cuenca (CHIRPS "
       "2001–2024); robustez: dic–mar.")

# 4. Placebo ----------------------------------------------------------------------------
f = []
for m in MEDIDAS:
    regs = [f"D_{m}", f"DE_{m}", f"D_{m}_f1", f"DE_{m}_f1"] + CONTROLES
    f += estimar(a[MA["placebo_f1"]], "fc_pp", regs,
                 {"adelanto t+1 (filo)": {f"D_{m}_f1": 1.0},
                  "adelanto t+1 (embalse)": {f"D_{m}_f1": 1.0, f"DE_{m}_f1": 1.0},
                  "b1 (filo) con adelanto": {f"D_{m}": 1.0}},
                 etiqueta={"medida": m, "variante": "adelanto 1"})
    s = ["_f1", "_f2", "_f3"]
    regs = [f"D_{m}", f"DE_{m}"] + [f"D_{m}{k}" for k in s] + [f"DE_{m}{k}" for k in s] + CONTROLES
    pr = {f"adelanto t+{k[-1]} (filo)": {f"D_{m}{k}": 1.0} for k in s}
    pr["suma adelantos (filo)"] = {f"D_{m}{k}": 1.0 for k in s}
    pr["b1 (filo) con adelantos"] = {f"D_{m}": 1.0}
    f += estimar(a[MA["placebo_f1_f3"]], "fc_pp", regs, pr, etiqueta={"medida": m, "variante": "adelantos 1–3"},
                 conjuntas={"Wald adelantos = 0 (filo)": [f"D_{m}{k}" for k in s]})
correr("4_placebo", f, "T7 · 4.3.4 Placebo con adelantos",
       "La deforestación futura no debería explicar el FC de hoy. Con la medida acumulada, el adelanto y el "
       "valor del año están muy correlacionados (el acumulado de t+1 = acumulado de t + flujo de t+1).")

# 5. Sin El Niño -------------------------------------------------------------------------
correr("5_sin_nino", principal_en(a, MA["sin_nino"], "sin 2009–10, 2015–16, 2023–24"),
       "T7 · 4.3.5 Sin años de El Niño", "Especificación principal sin 2009–2010, 2015–2016 y 2023–2024.")

# 6. Caudales -----------------------------------------------------------------------------
f = []
for y, ny in [("cv_diario", "CV del caudal diario (principal)"), ("q7min_rel", "caudal base 7 días / media (segunda)")]:
    for m in MEDIDAS:
        f += estimar(a[MA["caudales"]], y, [f"D_{m}"] + CONTROLES, {"D (todas las unidades)": {f"D_{m}": 1.0}},
                     etiqueta={"medida": m, "variante": f"{ny}"})
        f += estimar(a[MA["caudales"]], y, [f"D_{m}", f"DE_{m}"] + CONTROLES, pruebas_basicas(m),
                     etiqueta={"medida": m, "variante": f"{ny}, con interacción"})
        f += estimar(a[MA["caudales_sin_hueco"]], y, [f"D_{m}"] + CONTROLES, {"D (todas las unidades)": {f"D_{m}": 1.0}},
                     etiqueta={"medida": m, "variante": f"{ny}, sin hueco Chinchiná"})
correr("6_caudales", f, "T7 · 4.3.6 Caudales (mecanismo)",
       "Signo esperado si la deforestación quita regulación: positivo en el CV diario y negativo en el caudal "
       "base. Series de XM; unidades con `usar_prueba_mecanismo` y año completo de caudal.")

# 7. SMByC ---------------------------------------------------------------------------------
correr("7_smbyc", [{"medida": "—", "variante": "2013–2024 con deforestación del SMByC", "termino": "—",
                    "nota": "PENDIENTE: no hay datos del SMByC todavía. Muestra prevista: obs_principal y año ≥ 2013"}],
       "T7 · 4.3.7 Fuente alterna (SMByC)", "Pendiente.")

# 8. Muestra -------------------------------------------------------------------------------
f = []
f += principal_en(a, MA["sin_fc_mayor_1"], "sin FC > 1")
f += principal_en(a, MA["sin_meses_sin_registro"], "sin años con meses sin registro")
f += principal_en(a, MA["con_parciales"], "con años parciales (FC sobre horas en operación)", y="fc_horas_pp")
f += principal_en(a, MA["sin_miel_2001_2013"], "sin Miel I 2001–2013")
f += principal_en(a, MA["no_anidadas"], "solo cuencas no anidadas")
# regulación continua
for m in MEDIDAS:
    d = a[MA["regulacion"]].copy()
    d[f"DR_{m}"] = d[f"D_{m}"] * d["ln_reg"]
    f += estimar(d, "fc_pp", [f"D_{m}", f"DR_{m}"] + CONTROLES,
                 {"b1 (regulación 0 días)": {f"D_{m}": 1.0}, "D × ln(1+días)": {f"DR_{m}": 1.0}},
                 etiqueta={"medida": m, "variante": "regulación continua (sin Ínsula)"})
# cascada agrupada por sistema A
pr_ = a[MA["principal"]].copy()
horas = np.where(pr_["anio"] % 4 == 0, 8784, 8760)
pr_["cap_horas"] = pr_["cap_mw"] * horas
chk = (pr_["gen_gwh"] * 1000 / pr_["cap_horas"] - pr_["fc"]).abs()
assert chk.max() < 1e-3, f"FC no reproduce gen/(cap × horas): {chk.max()}"
pr_["cap_emb"] = pr_["cap_horas"] * pr_["embalse"]
sis = pr_.groupby(["sistema_geom_A", "anio"], as_index=False).agg(gen=("gen_gwh", "sum"), caph=("cap_horas", "sum"),
                                                                  emb=("cap_emb", "sum"))
sis["fc_pp"] = sis["gen"] * 1000 / sis["caph"] * 100
cuenca_mayor = (a[a["muestra_principal"].eq(1)].sort_values("ha_atch").groupby("sistema_geom_A")["unidad"].last())
emb_sis = (pr_.groupby("sistema_geom_A")["cap_emb"].sum() / pr_.groupby("sistema_geom_A")["cap_horas"].sum()).gt(0.5)
ref = a[a["unidad"].isin(cuenca_mayor.values)][["unidad", "anio", "lluvia", "trasv_guarino", "trasv_manso"]
                                               + [f"D_{m}" for m in MEDIDAS]]
ref["sistema_geom_A"] = ref["unidad"].map({v: k for k, v in cuenca_mayor.items()})
sis = sis.merge(ref.drop(columns="unidad"), on=["sistema_geom_A", "anio"], how="left")
sis["embalse"] = sis["sistema_geom_A"].map(emb_sis).astype(int)
sis["unidad"] = sis["sistema_geom_A"]
for m in MEDIDAS:
    sis[f"DE_{m}"] = sis[f"D_{m}"] * sis["embalse"]
    f += estimar(sis, "fc_pp", [f"D_{m}", f"DE_{m}"] + CONTROLES, pruebas_basicas(m),
                 etiqueta={"medida": m, "variante": "cascada agrupada por sistema A",
                           "nota": "cuenca mayor: " + ", ".join(f"{k}→{v}" for k, v in cuenca_mayor.items())
                                   + "; embalse: " + ", ".join(k for k, v in emb_sis.items() if v)})
correr("8_muestra", f, "T7 · 4.3.8 Muestra", "Variantes de muestra fijadas en 4.3.8 y la medida continua de "
       "regulación (prueba secundaria del registro de cambios, 17-nov).")

res = pd.concat(todas, ignore_index=True)
guardar(res, "t7_02_resumen_pruebas", "T7 · Pruebas de 4.3, todas", "Unión de las tablas t7_02_*.", COLS)
