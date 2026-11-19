"""
Tesis 2.0 · T5 · Descarga de XM (API pública servapibi.xm.com.co, con requests) + ONI (NOAA) + IPC (respaldo Banco Mundial).

Se corre en el Mac, desde la carpeta 03_tesis:

    python3 -m pip install pandas openpyxl requests     (ya no usa pydataxm: falla en Python 3.14)
    python3 03_codigo/03_xm/descargar_xm_t5.py              # todo (≈ 20–40 min la primera vez)
    python3 03_codigo/03_xm/descargar_xm_t5.py --prueba      # 1 mes de cada serie, sin guardar (1 min)
    python3 03_codigo/03_xm/descargar_xm_t5.py --solo listas # solo listados de ríos y embalses (1 min)
    python3 03_codigo/03_xm/descargar_xm_t5.py --solo ipc    # solo el IPC del Banco de la República

Qué baja (todo 2000-01-01 → 2024-12-31, sin filtros: todos los ríos / embalses del SIN;
el filtro por unidad se hace después en procesar_t5.py):

    Métrica XM            Entidad   Frecuencia  Para qué
    ListadoRios           Sistema   lista       relación río → unidad (código, nombre, región)
    ListadoEmbalses       Sistema   lista       relación embalse → unidad
    AporCaudal            Rio       diaria      aportes hídricos m3/s (pedido 2 y 6)
    VoluUtilDiarMasa      Embalse   diaria      volumen útil en Mm3 (pedido 3)
    PorcVoluUtilDiar      Embalse   diaria      % de volumen útil → capacidad útil en m3 (pedido 5)
    CapaUtilDiarMasa      Embalse   diaria      capacidad útil en m3 (pedido 5)
    PrecBolsNaci          Sistema   horaria     precio de bolsa (pedido 4; se baja 2000–2024 entero
                                                para comparar con los Excel viejos)

Además:
    ONI (NOAA CPC)       oni.ascii.txt                         (pedido 7)
    IPC respaldo         API Banco Mundial FP.CPI.TOTL (anual)  solo si no pusiste el IPC del DANE/BanRep

Salidas sin tocar en 02_datos/crudos/xm_t5/<Metrica>_<Entidad>_<AAAA>.csv y 02_datos/crudos/macro/.
Se puede interrumpir y volver a correr: no repite años ya bajados. Si un año falla, bórralo
(o no existe) y vuelve a correr.
"""
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / "02_datos" / "crudos" / "xm_t5"
MACRO = BASE / "02_datos" / "crudos" / "macro"
RAW.mkdir(parents=True, exist_ok=True)
MACRO.mkdir(parents=True, exist_ok=True)

ANIOS = range(2000, 2025)
SERIES = [  # (métrica, entidad)
    ("AporCaudal", "Rio"),
    ("VoluUtilDiarMasa", "Embalse"),
    ("PorcVoluUtilDiar", "Embalse"),
    ("CapaUtilDiarMasa", "Embalse"),
    ("PrecBolsNaci", "Sistema"),
]
LISTAS = ["ListadoRios", "ListadoEmbalses"]


URL = "https://servapibi.xm.com.co/{}"
TIPOS = {"HourlyEntities": "hourly", "DailyEntities": "daily"}


class API:
    """Cliente mínimo de la API de XM con requests (sin pydataxm).
    pydataxm usa asyncio + nest_asyncio, que falla en Python 3.14 ("Timeout context manager
    should be used inside a task"). Se hacen las mismas peticiones, una por mes, de forma síncrona."""

    def __init__(self):
        import requests
        self.s = requests.Session()
        r = self.s.post(URL.format("Lists"), json={"MetricId": "ListadoMetricas"}, timeout=120)
        r.raise_for_status()
        inv = pd.json_normalize(r.json()["Items"], "ListEntities", "Date", sep="_")
        inv.columns = [c.replace("Values_", "") for c in inv.columns]
        self.inventario_metricas = inv

    def tipo(self, metrica, entidad):
        t = self.inventario_metricas.query("MetricId == @metrica and Entity == @entidad").Type
        return t.iloc[0] if len(t) else None

    def request_data(self, metrica, entidad, ini, fin):
        t = self.tipo(metrica, entidad)
        if t == "ListsEntities" or metrica.startswith("Listado"):
            r = self.s.post(URL.format("Lists"), json={"MetricId": metrica, "Entity": entidad}, timeout=120)
            r.raise_for_status()
            return pd.json_normalize(r.json()["Items"], "ListEntities", "Date", sep="_")
        base = TIPOS.get(t, "daily")
        partes = []
        for p0 in pd.date_range(pd.Timestamp(ini).replace(day=1), fin, freq="MS"):
            a, b = max(p0, pd.Timestamp(ini)), min(p0 + pd.offsets.MonthEnd(0), pd.Timestamp(fin))
            body = {"MetricId": metrica, "StartDate": a.strftime("%Y-%m-%d"), "EndDate": b.strftime("%Y-%m-%d"),
                    "Entity": entidad, "Filter": []}
            r = self.s.post(URL.format(base), json=body, timeout=180)
            r.raise_for_status()
            items = r.json().get("Items") or []
            if items:
                partes.append(pd.json_normalize(items, t or "DailyEntities", "Date", sep="_"))
        return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def api():
    return API()


def pedir(x, metrica, entidad, ini, fin, intentos=3):
    for k in range(intentos):
        try:
            df = x.request_data(metrica, entidad, ini, fin)
            return df if df is not None else pd.DataFrame()
        except Exception as e:  # la API se cae a ratos: reintenta
            print(f"    intento {k + 1}: {e}")
            time.sleep(5 * (k + 1))
    return None


def inventario(x):
    inv = getattr(x, "inventario_metricas", None)
    if inv is not None:
        inv.to_csv(RAW / "_inventario_metricas_xm.csv", index=False, encoding="utf-8-sig")
        return set(zip(inv.MetricId, inv.Entity))
    return set()


def bajar_listas(x):
    hoy = date(2024, 12, 31)
    for m in LISTAS:
        f = RAW / f"{m}.csv"
        if f.exists():
            continue
        df = pedir(x, m, "Sistema", hoy, hoy)
        if df is None or df.empty:
            print(f"  {m}: sin datos")
            continue
        df.to_csv(f, index=False, encoding="utf-8-sig")
        print(f"  {m}: {len(df)} filas")


def bajar_series(x, disponibles):
    for metrica, entidad in SERIES:
        if disponibles and (metrica, entidad) not in disponibles:
            print(f"!! {metrica}/{entidad} no aparece en el inventario de XM: se intenta igual")
        for a in ANIOS:
            f = RAW / f"{metrica}_{entidad}_{a}.csv"
            if f.exists():
                continue
            print(f"  {metrica} {entidad} {a}…", flush=True)
            df = pedir(x, metrica, entidad, date(a, 1, 1), date(a, 12, 31))
            if df is None:
                print(f"    {a}: falló; vuelve a correr el script más tarde")
                continue
            df.to_csv(f, index=False, encoding="utf-8-sig")  # se guarda aunque venga vacío: queda registrado
            print(f"    {len(df)} filas")


def bajar_oni():
    import requests
    f = MACRO / "oni_noaa.txt"
    if f.exists():
        return
    url = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    f.write_text(r.text)
    print(f"  ONI: {len(r.text.splitlines())} líneas ({url})")


IPC_BANREP = ("https://totoro.banrep.gov.co/analytics/saw.dll?Download&Format=excel2007&Extension=.xlsx&BypassCache=true"
              "&path=%2Fshared%2FSeries%20Estad%C3%ADsticas_T%2F1.%20IPC%20base%202018%2F1.2.%20Por%20a%C3%B1o"
              "%2F1.2.5.IPC_Serie_variaciones&lang=es")


def bajar_ipc_banrep():
    """IPC total nacional mensual (DANE, base dic-2018 = 100, empalmado desde 1954) publicado por el Banco
    de la República, serie 1.2.5. Se guarda tal cual en crudos/macro/ipc_banrep.xlsx."""
    import requests
    f = MACRO / "ipc_banrep.xlsx"
    if f.exists():
        return
    r = requests.get(IPC_BANREP, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    if not r.content.startswith(b"PK"):  # un .xlsx es un zip; si no, BanRep devolvió una página
        raise RuntimeError("BanRep no devolvió un Excel; bájalo a mano (ver LEEME_T5.md)")
    f.write_bytes(r.content)
    print(f"  IPC Banco de la República: {len(r.content) // 1024} KB")


def bajar_ipc_dane():
    """IPC del DANE, "Índices – series de empalme" (anex-IPC-Indices-<mes><año>.xlsx). El nombre cambia con cada
    publicación: se prueba el mes actual y los 12 anteriores. Se guarda tal cual en crudos/macro/ipc_dane.xlsx."""
    import requests
    f = MACRO / "ipc_dane.xlsx"
    if f.exists():
        return
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    hoy = date.today()
    for k in range(13):
        a, m = hoy.year, hoy.month - k
        while m < 1:
            a, m = a - 1, m + 12
        url = f"https://www.dane.gov.co/files/operaciones/IPC/{meses[m - 1]}{a}/anex-IPC-Indices-{meses[m - 1]}{a}.xlsx"
        r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and r.content.startswith(b"PK"):
            f.write_bytes(r.content)
            (MACRO / "ipc_dane_fuente.txt").write_text(url + "\n")
            print(f"  IPC DANE: {url} ({len(r.content) // 1024} KB)")
            return
    raise RuntimeError("no encontré el anexo de índices del DANE; bájalo a mano (ver LEEME_T5.md)")


def bajar_ipc_respaldo():
    """IPC anual (2010 = 100) del Banco Mundial, fuente original DANE vía FMI. Es respaldo:
    procesar_t5.py prefiere 02_datos/crudos/macro/ipc_dane.xlsx o ipc_banrep.xlsx si existen."""
    import requests
    f = MACRO / "ipc_bancomundial_anual.csv"
    if f.exists():
        return
    url = "https://api.worldbank.org/v2/country/COL/indicator/FP.CPI.TOTL?format=json&per_page=200"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    filas = [dict(anio=int(d["date"]), ipc=d["value"]) for d in r.json()[1] if d["value"] is not None]
    pd.DataFrame(filas).sort_values("anio").to_csv(f, index=False)
    print(f"  IPC respaldo Banco Mundial: {len(filas)} años")


def main():
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    x = api()
    if "--prueba" in sys.argv:  # 1 mes de cada serie, sin guardar: verifica que la API responde
        for metrica, entidad in SERIES:
            df = pedir(x, metrica, entidad, date(2020, 1, 1), date(2020, 1, 31))
            print(f"  {metrica:18s} {entidad:8s} ene-2020: " + ("FALLÓ" if df is None else f"{len(df)} filas, columnas {list(df.columns)}"))
        return
    disp = inventario(x)
    print("Listados de ríos y embalses…")
    bajar_listas(x)
    if solo == "listas":
        return
    if solo == "ipc":
        for fn in (bajar_ipc_dane, bajar_ipc_banrep):
            try:
                fn()
            except Exception as e:
                print(f"  {fn.__name__}: {e}")
        return
    print("Series XM 2000–2024…")
    bajar_series(x, disp)
    print("ONI e IPC…")
    for fn in (bajar_oni, bajar_ipc_dane, bajar_ipc_banrep, bajar_ipc_respaldo):
        try:
            fn()
        except Exception as e:
            print(f"  {fn.__name__}: {e}")
    print("\nListo. Ahora corre: python3 03_codigo/03_xm/procesar_t5.py")


if __name__ == "__main__":
    main()
