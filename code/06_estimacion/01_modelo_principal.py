"""
T7 · 01 · Conteo de observaciones y modelo principal (secciones 4.2 y 4.5).

Salidas en 07_salidas/tablas/:
  t7_00_conteo_observaciones.csv/.md   conteos recalculados (lógica de construir_panel.py) y esperados de T6
  t7_01_modelo_principal.csv/.md       b1, b2, b1 + b2, lluvia y trasvases, por medida
  t7_01_criterio_4_5.csv/.md           evaluación de cada medida contra el criterio fijado
"""
import pandas as pd

from t7_comun import (CONTROLES, ESPERADO, MEDIDAS, cargar_anual, cargar_mensual, conteo, estimar,
                      guardar, muestras_anuales, muestras_mensuales, pruebas_basicas)

a, mm = cargar_anual(), cargar_mensual()
MA, MM = muestras_anuales(a), muestras_mensuales(mm)

# 0. Conteo -----------------------------------------------------------------------------
cnt = pd.DataFrame([conteo(a, v, k) for k, v in MA.items()] + [conteo(mm, v, k) for k, v in MM.items()])
for k, n in ESPERADO.items():
    obs = int(cnt.loc[cnt["muestra"].eq(k), "obs"].iloc[0])
    assert obs == n, f"Conteo {k}: {obs} ≠ {n} esperado de T6"
p = a[MA["principal"]]
assert p["unidad"].nunique() == 26 and p["sistema_geom_A"].nunique() == 10
guardar(cnt, "t7_00_conteo_observaciones", "T7 · Conteo de observaciones por muestra",
        "Recalculado con la lógica de `construir_panel.py` (sección 6). La columna `esperado_T6` trae los "
        "valores de `conteo_observaciones.csv`; el script falla si no coinciden.")

# 1. Modelo principal -------------------------------------------------------------------
filas = []
for m, (_, etiqueta, _) in MEDIDAS.items():
    regs = [f"D_{m}", f"DE_{m}"] + CONTROLES
    pr = {**pruebas_basicas(m), "lluvia (miles de mm)": {"lluvia": 1.0},
          "trasvase Guarinó": {"trasv_guarino": 1.0}, "trasvase Manso": {"trasv_manso": 1.0}}
    filas += estimar(a[MA["principal"]], "fc_pp", regs, pr, etiqueta={"medida": m, "etiqueta": etiqueta})
res = pd.DataFrame(filas)
cols = ["medida", "termino", "estimado", "ee", "t", "p_conv", "p_wcb", "N", "unidades", "G", "omitidos"]
guardar(res, "t7_01_modelo_principal", "T7 · Modelo principal (4.2 y 4.5)",
        "FC en puntos porcentuales. Efectos fijos de unidad y año; lluvia (miles de mm) y control de trasvase "
        "de Miel I. Errores agrupados por sistema hídrico A (10). `p_conv`: CRV1, t con G − 1 gl. `p_wcb`: wild "
        "cluster restricted bootstrap, pesos de Webb, 9.999 réplicas. Prueba de b1 + b2 = 0: F = t².", cols)

# 2. Criterio de 4.5 --------------------------------------------------------------------
crit = []
for m, (_, etiqueta, _) in MEDIDAS.items():
    r = res[res["medida"].eq(m)].set_index("termino")
    b1, s = r.loc["b1 (filo)"], r.loc["b1 + b2 (embalse)"]
    crit.append({
        "medida": etiqueta, "b1": b1["estimado"], "p_b1_conv": b1["p_conv"], "p_b1_wcb": b1["p_wcb"],
        "b1<0 y p<0,05 (conv)": "sí" if (b1["estimado"] < 0 and b1["p_conv"] < 0.05) else "no",
        "b1<0 y p<0,05 (WCB)": "sí" if (b1["estimado"] < 0 and b1["p_wcb"] < 0.05) else "no",
        "b1+b2": s["estimado"], "F(b1+b2=0)": s["t"] ** 2, "p_F_conv": s["p_conv"], "p_F_wcb": s["p_wcb"],
        "b1+b2=0 no se rechaza (conv)": "sí" if s["p_conv"] >= 0.05 else "no",
        "b1+b2=0 no se rechaza (WCB)": "sí" if s["p_wcb"] >= 0.05 else "no",
    })
crit = pd.DataFrame(crit)
guardar(crit, "t7_01_criterio_4_5", "T7 · Criterio de la hipótesis (4.5), por medida",
        "Criterio fijado: b1 < 0 con p < 0,05 (dos colas) y prueba F de b1 + b2 = 0. Se evalúa con el p-valor "
        "convencional y con el del bootstrap; si no coinciden, se reportan los dos.")
print(res[cols].round(4).to_string())
print(crit.round(4).T.to_string())
