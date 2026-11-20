"""
T7 · 07 · Valoración (sección 4.4), con los supuestos que decidió Jorge el 20-nov-2026 (registro de cambios,
commit 7f76ba5, antes de calcular).

- Coeficiente: b1 de la medida acumulada (07_salidas/tablas/t7_01_modelo_principal.csv), solo unidades a filo;
  embalse = 0. Rango con el intervalo de 95 % convencional (CRV1, t con 9 gl). El p del bootstrap (0,29) indica
  que el intervalo del bootstrap incluye el cero: el valor es ilustrativo.
- Energía perdida del año (MWh) = (−b1 / 100) × def_acum_pct × capacidad (MW) × horas del año.
- Valor histórico 2001–2024: cada año a su precio de bolsa en pesos de 2024 (precio_bolsa_cop2024_kwh).
- Valor a futuro 2025–2054 (30 años): deforestación y capacidad de 2024 constantes (sin nueva pérdida ni
  recuperación); solo unidades que operaban en 2024. Precio central = promedio 2001–2024; alto = 2024; bajo =
  mediana 2001–2024. Tasa escalonada de la Resolución 1092 de 2022 del DNP: 9,5 % años 1–5, 6,4 % años 6–25,
  3,5 % desde el año 26. Sensibilidad: 9 % fija, 3,5 % fija y perpetuidad (después del año 30, a 3,5 %).
- Por hectárea: valor dividido por las hectáreas de bosque perdidas hasta 2024 (def_acum_ha). El agregado usa la
  suma simple de hectáreas, que cuenta dos veces las cuencas anidadas: es una cota inferior del valor por hectárea.
- Política: parte del valor en centrales de más de 10 MW (las obligadas a pagar transferencias).

Salidas: t7_07_valoracion_historica, t7_07_valoracion_futura, t7_07_valoracion_por_unidad, t7_07_valoracion_resumen.
"""
import numpy as np
import pandas as pd
from scipy import stats

from t7_comun import TAB, a_markdown, cargar_anual, guardar

a = cargar_anual()
mp = pd.read_csv(TAB / "t7_01_modelo_principal.csv")
r = mp[(mp["medida"] == "acum_pct") & (mp["termino"] == "b1 (filo)")].iloc[0]
q = stats.t.ppf(0.975, r["G"] - 1)
B = {"central": r["estimado"], "IC 95 % (menos efecto)": r["estimado"] + q * r["ee"],
     "IC 95 % (más efecto)": r["estimado"] - q * r["ee"]}

f = a[a["obs_principal"].eq(1) & a["embalse"].eq(0)].copy()
f["horas"] = np.where(f["anio"] % 4 == 0, 8784, 8760)
precio = a.groupby("anio")["precio_bolsa_cop2024_kwh"].first()
P = {"central (promedio 2001–2024)": precio.mean(), "alto (2024)": precio.loc[2024],
     "bajo (mediana 2001–2024)": precio.median()}

# histórico ----------------------------------------------------------------------------------------
hist = []
for nb, b in B.items():
    e = (-b / 100) * f["def_acum_pct"] * f["cap_mw"] * f["horas"]          # MWh
    v = e * 1000 * f["precio_bolsa_cop2024_kwh"]                          # pesos de 2024
    hist.append({"escenario_coeficiente": nb, "b1": b, "energia_perdida_GWh": e.sum() / 1000,
                 "valor_miles_millones_cop2024": v.sum() / 1e9,
                 "valor_2024_miles_millones": v[f["anio"].eq(2024)].sum() / 1e9,
                 "parte_centrales_mayor_10MW_%": 100 * v[f["cap_mw"].gt(10)].sum() / v.sum()})
    if nb == "central":
        f["energia_perdida_MWh"], f["valor_cop2024"] = e, v
hist = pd.DataFrame(hist)
anual = f.groupby("anio").agg(energia_perdida_GWh=("energia_perdida_MWh", lambda s: s.sum() / 1000),
                              valor_miles_millones=("valor_cop2024", lambda s: s.sum() / 1e9)).reset_index()
guardar(hist, "t7_07_valoracion_historica", "T7 · Valoración histórica 2001–2024 (centrales a filo)",
        "Energía perdida por la deforestación acumulada, valorada cada año a su precio de bolsa en pesos de 2024. "
        "Miles de millones de pesos de 2024.\n\nPor año (escenario central):\n\n" + a_markdown(anual))
anual.to_csv(TAB / "t7_07_valoracion_historica_por_anio.csv", index=False)

# futuro ---------------------------------------------------------------------------------------------
u24 = f[f["anio"].eq(2024)].copy()          # unidades que operaban en 2024
k = np.arange(1, 31)
TASAS = {"escalonada DNP (9,5 / 6,4 / 3,5 %)": np.where(k <= 5, 0.095, np.where(k <= 25, 0.064, 0.035)),
         "9 % fija": np.full(30, 0.09), "3,5 % fija": np.full(30, 0.035)}
fut = []
for nb, b in B.items():
    e24 = ((-b / 100) * u24["def_acum_pct"] * u24["cap_mw"] * 8760).sum()   # MWh por año
    for npz, p in P.items():
        anual_v = e24 * 1000 * p
        for nt, rr in TASAS.items():
            fd = np.cumprod(1 / (1 + rr))
            vp30 = (anual_v * fd).sum()
            fila = {"escenario_coeficiente": nb, "precio": npz, "precio_cop_kwh": p, "tasa": nt,
                    "energia_perdida_anual_GWh": e24 / 1000, "valor_anual_miles_millones": anual_v / 1e9,
                    "valor_presente_30_anios_miles_millones": vp30 / 1e9}
            if nt.startswith("escalonada"):
                fila["valor_presente_perpetuidad_miles_millones"] = (vp30 + anual_v / 0.035 * fd[-1]) / 1e9
            fut.append(fila)
fut = pd.DataFrame(fut)
guardar(fut, "t7_07_valoracion_futura", "T7 · Valoración a futuro, 30 años (centrales a filo que operaban en 2024)",
        "Deforestación y capacidad de 2024 constantes. Miles de millones de pesos de 2024.")

# por unidad y por hectárea ---------------------------------------------------------------------------
pu = f.groupby("unidad").agg(cap_mw_2024=("cap_mw", "last"), anios=("anio", "size"),
                             valor_historico_miles_millones=("valor_cop2024", lambda s: s.sum() / 1e9),
                             def_acum_pct_ultimo=("def_acum_pct", "last"), ha_perdidas=("def_acum_ha", "last"),
                             ultimo_anio=("anio", "max")).reset_index()
fd = np.cumprod(1 / (1 + TASAS["escalonada DNP (9,5 / 6,4 / 3,5 %)"]))
u24["vp30"] = (-B["central"] / 100) * u24["def_acum_pct"] * u24["cap_mw"] * 8760 * 1000 * P["central (promedio 2001–2024)"] * fd.sum()
pu = pu.merge(u24[["unidad", "vp30"]], on="unidad", how="left")
pu["vp30_miles_millones"] = pu.pop("vp30") / 1e9
pu["vp30_por_ha_millones_cop"] = pu["vp30_miles_millones"] * 1e3 / pu["ha_perdidas"]
pu["historico_por_ha_millones_cop"] = pu["valor_historico_miles_millones"] * 1e3 / pu["ha_perdidas"]
guardar(pu, "t7_07_valoracion_por_unidad", "T7 · Valoración por unidad a filo (escenario central)",
        "Valor presente a 30 años con precio promedio 2001–2024 y tasa escalonada del DNP. Hectáreas: bosque perdido "
        "en la cuenca hasta el último año de la unidad en la muestra.")

c = fut[(fut["escenario_coeficiente"] == "central") & fut["precio"].str.startswith("central") & fut["tasa"].str.startswith("escalonada")].iloc[0]
ha24 = u24["def_acum_ha"].sum()
resumen = pd.DataFrame([
    {"concepto": "b1 acumulado (pp de FC por punto de bosque perdido)", "valor": B["central"]},
    {"concepto": "Valor histórico 2001–2024, miles de millones de pesos de 2024", "valor": hist.iloc[0]["valor_miles_millones_cop2024"]},
    {"concepto": "Energía perdida 2001–2024, GWh", "valor": hist.iloc[0]["energia_perdida_GWh"]},
    {"concepto": "Valor anual a precio promedio, miles de millones", "valor": c["valor_anual_miles_millones"]},
    {"concepto": "Valor presente 30 años (central), miles de millones", "valor": c["valor_presente_30_anios_miles_millones"]},
    {"concepto": "Hectáreas de bosque perdidas hasta 2024 (suma simple, unidades que operaban en 2024)", "valor": ha24},
    {"concepto": "Valor presente 30 años por hectárea perdida, millones de pesos (cota inferior)",
     "valor": c["valor_presente_30_anios_miles_millones"] * 1e3 / ha24},
    {"concepto": "Parte del valor histórico en centrales de más de 10 MW, %", "valor": hist.iloc[0]["parte_centrales_mayor_10MW_%"]},
])
guardar(resumen, "t7_07_valoracion_resumen", "T7 · Valoración, resumen (escenario central)",
        "Ilustrativo: el coeficiente no pasa el bootstrap (p 0,29). Rangos en las otras tablas t7_07.")
print(hist.round(3).to_string()); print(fut.round(2).to_string()); print(pu.round(2).to_string()); print(resumen.round(3).to_string())
print("precios", {k: round(v, 1) for k, v in P.items()}, "b1", {k: round(v, 3) for k, v in B.items()})
