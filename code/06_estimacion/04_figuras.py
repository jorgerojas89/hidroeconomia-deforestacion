"""
T7 · 04 · Figuras a partir de las tablas de 07_salidas/tablas/ (correr después de 01–03).

  t7_fig1_coeficientes.png   b1 (filo) y b1 + b2 (embalse) con IC 95 % (CRV1) en el modelo principal y en
                             las pruebas, por medida; a la derecha el p-valor del bootstrap de b1
  t7_fig2_por_unidad.png     coeficiente de cada regresión por unidad, por tipo
  t7_fig3_influencia.png     b1 al quitar una unidad o un sistema a la vez
Colores: filo azul #2a78d6, embalse naranja #eb6834 (paleta categorical validada, ranuras 1 y 2).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from t7_comun import FIG, MEDIDAS, TAB

AZUL, NARANJA, GRIS, TINTA, TINTA2 = "#2a78d6", "#eb6834", "#d9d8d4", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRIS, "axes.labelcolor": TINTA2, "xtick.color": TINTA2,
                     "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
ETQ = {m: v[1] for m, v in MEDIDAS.items()}


def nom(u: str) -> str:
    return u.title().replace(" Iii", " III").replace(" Ii", " II").replace(" I ", " I ")

p = pd.read_csv(TAB / "t7_01_modelo_principal.csv")
p["prueba"], p["variante"] = "1_principal", "Modelo principal"
r = pd.concat([p, pd.read_csv(TAB / "t7_02_resumen_pruebas.csv")], ignore_index=True)
r = pd.concat([r, pd.read_csv(TAB / "t7_03_errores_alternativos.csv").assign(prueba="9_errores")], ignore_index=True)
FILAS = [("1_principal", "Modelo principal", "Principal"),
         ("2_rezagos", "rezagos 0–3", "Rezagos: suma t…t−3"),
         ("3_epoca_seca", "seca propia (principal)", "Mensual, época seca propia"),
         ("3_epoca_seca", "dic–mar (robustez)", "Mensual, dic–mar"),
         ("3_epoca_seca", "meses no secos", "Mensual, meses no secos"),
         ("5_sin_nino", "sin 2009–10, 2015–16, 2023–24", "Sin años de El Niño"),
         ("8_muestra", "sin FC > 1", "Sin FC > 1"),
         ("8_muestra", "sin años con meses sin registro", "Sin años con meses sin registro"),
         ("8_muestra", "con años parciales (FC sobre horas en operación)", "Con años parciales"),
         ("8_muestra", "sin Miel I 2001–2013", "Sin Miel I 2001–2013"),
         ("8_muestra", "solo cuencas no anidadas", "Solo cuencas no anidadas"),
         ("8_muestra", "cascada agrupada por sistema A", "Cascada agrupada por sistema")]
T_FILO = {"2_rezagos": "suma b1 t…t-3 (filo)"}
T_EMB = {"2_rezagos": "suma b1+b2 t…t-3 (embalse)"}

fig, axes = plt.subplots(1, 3, figsize=(13, 6.2), sharey=True)
for ax, m in zip(axes, MEDIDAS):
    for i, (pr, var, et) in enumerate(FILAS):
        for t, col, dy in [(T_FILO.get(pr, "b1 (filo)"), AZUL, -0.15), (T_EMB.get(pr, "b1 + b2 (embalse)"), NARANJA, 0.15)]:
            s = r[(r["prueba"] == pr) & (r["variante"] == var) & (r["medida"] == m) & (r["termino"] == t)]
            if s.empty:
                continue
            s = s.iloc[0]
            q = stats.t.ppf(0.975, s["G"] - 1)
            y = i + dy
            ax.plot([s["estimado"] - q * s["ee"], s["estimado"] + q * s["ee"]], [y, y], color=col, lw=2,
                    solid_capstyle="round")
            ax.plot(s["estimado"], y, "o", ms=6, color=col, mec="#fcfcfb", mew=1.5)
            if col == AZUL:
                ax.text(1.02, y, f"{s['p_wcb']:.2f}", transform=ax.get_yaxis_transform(), fontsize=7.5,
                        color=TINTA2, va="center")
    ax.axvline(0, color=TINTA2, lw=0.8)
    ax.set_title(ETQ[m], fontsize=9.5, color=TINTA, loc="left")
    ax.set_xlabel("Puntos de FC por unidad de D")
    ax.grid(axis="x", color=GRIS, lw=0.5)
axes[0].set_yticks(range(len(FILAS)), [f[2] for f in FILAS])
axes[0].invert_yaxis()
axes[0].plot([], [], "o-", color=AZUL, label="b1, filo de agua")
axes[0].plot([], [], "o-", color=NARANJA, label="b1 + b2, embalse")
fig.legend(loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
fig.text(0.99, 0.01, "Número a la derecha de cada panel: p-valor WCR de b1 (Webb, 9.999 réplicas). "
         "Barras: IC 95 % CRV1 por sistema A, t con G−1 gl.", ha="right", fontsize=7.5, color=TINTA2)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(FIG / "t7_fig1_coeficientes.png", dpi=200)

# fig 2 por unidad -------------------------------------------------------------------------
pu = pd.read_csv(TAB / "t7_03_por_unidad.csv").dropna(subset=["b"])
fig, axes = plt.subplots(1, 3, figsize=(13, 6.5))
for ax, m in zip(axes, MEDIDAS):
    d = pu[pu["medida"] == m].sort_values(["tipo", "b"], ascending=[False, True]).reset_index(drop=True)
    for i, s in d.iterrows():
        col = AZUL if s["tipo"] == "filo" else NARANJA
        ax.plot([s["b"] - 1.96 * s["ee"], s["b"] + 1.96 * s["ee"]], [i, i], color=col, lw=2, alpha=0.9)
        ax.plot(s["b"], i, "o", ms=5 if s["n"] >= 10 else 4, color=col if s["n"] >= 10 else "#fcfcfb",
                mec=col, mew=1.5)
    ax.set_yticks(range(len(d)), [f"{nom(u)} ({n})" for u, n in zip(d["unidad"], d["n"])], fontsize=7)
    ax.invert_yaxis()
    ax.axvline(0, color=TINTA2, lw=0.8)
    lo, hi = np.nanpercentile(d["b"] - 1.96 * d["ee"], 10), np.nanpercentile(d["b"] + 1.96 * d["ee"], 90)
    ax.set_xlim(lo - 0.1 * abs(lo), hi + 0.1 * abs(hi))
    ax.set_title(ETQ[m], fontsize=9.5, color=TINTA, loc="left")
    ax.set_xlabel("Coeficiente de D (puntos de FC)")
    ax.grid(axis="x", color=GRIS, lw=0.5)
axes[0].plot([], [], "o-", color=AZUL, label="Filo de agua")
axes[0].plot([], [], "o-", color=NARANJA, label="Embalse")
fig.legend(loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
fig.text(0.99, 0.01, "Regresión por unidad: FC ~ D + lluvia + ONI + tendencia; IC 95 % Newey-West. Punto hueco: "
         "menos de 10 años. Eje recortado a los percentiles 10–90 de los intervalos.", ha="right", fontsize=7.5,
         color=TINTA2)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(FIG / "t7_fig2_por_unidad.png", dpi=200)

# fig 3 influencia ---------------------------------------------------------------------------
inf = pd.read_csv(TAB / "t7_03_influencia.csv")
inf = inf[inf["termino"] == "b1 (filo)"]
fig, axes = plt.subplots(1, 3, figsize=(13, 6.5), sharey=True)
orden = sorted(inf.loc[inf["variante"] == "sin la unidad", "excluido"].unique())
filas = [("sin la unidad", u) for u in orden] + [("sin el sistema A", s) for s in
                                                  sorted(inf.loc[inf["variante"] == "sin el sistema A", "excluido"].unique())]
for ax, m in zip(axes, MEDIDAS):
    base = p[(p["medida"] == m) & (p["termino"] == "b1 (filo)")].iloc[0]["estimado"]
    for i, (v, e) in enumerate(filas):
        s = inf[(inf["medida"] == m) & (inf["variante"] == v) & (inf["excluido"] == e)].iloc[0]
        q = stats.t.ppf(0.975, s["G"] - 1)
        col = AZUL if v == "sin la unidad" else TINTA2
        ax.plot([s["estimado"] - q * s["ee"], s["estimado"] + q * s["ee"]], [i, i], color=col, lw=1.6, alpha=0.8)
        ax.plot(s["estimado"], i, "o", ms=4.5, color=col, mec="#fcfcfb", mew=1)
    ax.axvline(0, color=TINTA2, lw=0.8)
    ax.axvline(base, color=AZUL, lw=0.8, ls="--")
    ax.set_title(ETQ[m], fontsize=9.5, color=TINTA, loc="left")
    ax.set_xlabel("b1 (filo), puntos de FC")
    ax.grid(axis="x", color=GRIS, lw=0.5)
axes[0].set_yticks(range(len(filas)), [("− " if v == "sin la unidad" else "− sistema ") + nom(e) for v, e in filas],
                   fontsize=7)
axes[0].invert_yaxis()
fig.text(0.99, 0.01, "Línea discontinua: b1 del modelo principal. IC 95 % CRV1 por sistema A.", ha="right",
         fontsize=7.5, color=TINTA2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "t7_fig3_influencia.png", dpi=200)
print("Figuras en", FIG)
