"""
Tesis 2.0 · T2 · Tabla maestra de centrales.

Una fila por unidad de panel: la central, o el grupo de centrales que XM reporta
junto (ALBAN = Alto + Bajo Anchicayá; GUATRON = Guadalupe III + IV + Troneras;
PAJARITO = Pajarito I + II).

Uso (desde 03_tesis):  python3 03_codigo/00_tabla_maestra/construir_tabla_maestra.py

Salidas en 02_datos/tabla_maestra/:
    tabla_maestra.csv        una fila por unidad (muestra 2019 + centrales con delimitación IGAC ok/Rev)
    componentes.csv          una fila por central o proyecto IGAC, con su unidad
    casos_dudosos.csv        lo que Jorge debe decidir
    generacion_xm_anual_2000_2018.csv   generación anual por nombre XM (insumo para revisar fechas)

Decisiones de Jorge: se escriben en la columna `decision` de casos_dudosos.csv
o directamente en el diccionario CORRECCIONES de abajo, y se vuelve a correr.
"""
from pathlib import Path
import re, unicodedata, math
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
D = BASE / "02_datos"
CR = D / "crudos"
OUT = D / "tabla_maestra"
OUT.mkdir(exist_ok=True)

# Estados del reporte IGAC que cuentan como delimitación usable (decisión de Jorge, 17-nov-2026)
ESTADOS_IGAC_VALIDOS = {"ok", "rev"}

# Correcciones manuales que Jorge vaya decidiendo: {unidad: {columna: valor}}
CORRECCIONES = {   # decisiones de Jorge, 17-nov-2026 (detalle en 02_datos/tabla_maestra/decisiones_jorge.csv)
    "ESMERALDA": {"tipo_propuesto": "filo", "fuentes_tipo": "decisión Jorge 17-nov-2026 (XM: filo)"},
    "SAN FRANCISCO": {"tipo_propuesto": "filo", "fuentes_tipo": "decisión Jorge 17-nov-2026 (XM: filo)"},
    "CHARQUITO": {"tipo_propuesto": "embalse", "fuentes_tipo": "decisión Jorge 17-nov-2026: regulada por el embalse del Muña"},
    "EL LIMONAR": {"tipo_propuesto": "embalse", "fuentes_tipo": "decisión Jorge 17-nov-2026: regulada por el embalse del Muña"},
    "TEQUENDAMA": {"tipo_propuesto": "embalse", "fuentes_tipo": "decisión Jorge 17-nov-2026: regulada por el embalse del Muña"},
    "RIOGRANDE I": {"tipo_propuesto": "embalse", "fuentes_tipo": "decisión Jorge 17-nov-2026: embalse Quebradona"},
    "SANTA ANA": {"rio": "sin río: toma agua por canales (acueducto de Bogotá)", "sistema_hidrico_propuesto": "CANALES ACUEDUCTO BOGOTA"},
    "RIONEGRO": {"rio": "sin río: toma agua por canales", "sistema_hidrico_propuesto": "CANALES"},
    "RIO PIEDRAS": {"lon": -75.772656, "lat": 5.791490, "rio": "Río Piedras"},
    "ITUANGO": {"tipo_propuesto": "embalse", "fuentes_tipo": "decisión Jorge 17-nov-2026: embalse confirmado (embalse sobre el río Cauca; entró en 2022)"},
    # CHEC (18-nov-2026): XM lista a EPM como agente de las centrales de la CHEC (Grupo EPM); Jorge: Municipal es de la CHEC
    "MUNICIPAL": {"agente": "CENTRAL HIDROELECTRICA DE CALDAS S.A. E.S.P. (CHEC; en XM figura EPM, Grupo EPM)"},
    "INSULA": {"agente": "CENTRAL HIDROELECTRICA DE CALDAS S.A. E.S.P. (CHEC; en XM figura EPM, Grupo EPM)"},
    "ESMERALDA": {"agente": "CENTRAL HIDROELECTRICA DE CALDAS S.A. E.S.P. (CHEC; en XM figura EPM, Grupo EPM)"},
    "SAN FRANCISCO": {"agente": "CENTRAL HIDROELECTRICA DE CALDAS S.A. E.S.P. (CHEC; en XM figura EPM, Grupo EPM)"},
    "RIO GRANDE": {"tipo_propuesto": "embalse", "fuentes_tipo": "decisión Jorge 17-nov-2026: en cadena del río Grande, con embalse que le permite generar o no (regulación); cuenca = ATCH oficial IGAC Quebrada Mocorongo"},
}
# Exclusiones del análisis (la unidad sigue en la tabla, con el motivo)
# Decisión de Jorge (17-nov-2026): todas las de acueducto salen del análisis; la evidencia queda escrita.
ACUEDUCTO = {
    "NIQUIA": "Turbina agua de Riogrande II que va a la planta de potabilización Manantiales (Niquía)",
    "AYURA": "EPM: asociada al embalse La Fe; contribuye al sistema de acueducto (planta La Ayurá)",
    "MANANTIALES": "Minicentral en la planta de potabilización Manantiales (EPM, alimentada por Riogrande II); verificar",
    "SANTA ANA": "Central del Acueducto de Bogotá (EAAB), proyecto MDL Santa Ana",
    "NIMA": "La base de 2019 la clasificaba en la cadena 'Acueducto'; verificar",
    "PIEDRAS BLANCAS": "Embalse Piedras Blancas del acueducto de EPM; además deja de generar en 2012",
    "AMERICA": "Microcentral en tanque del acueducto de EPM",
    "BELLO": "Microcentral en tanque del acueducto de EPM",
    "CAMPESTRE (EPM)": "Microcentral en tanque del acueducto de EPM",
    "NUTIBARA": "Microcentral en tanque del acueducto de EPM",
    "PAT EL DORADO": "Turbina en la conducción del tanque El Dorado (acueducto EPM, Envigado)",
    "INTERMEDIA": "Planta de acueducto: confirmado por EPM a Jorge, 17-nov-2026",
    "SAN CANCIO": "Planta de acueducto: confirmado por EPM a Jorge, 17-nov-2026",
}
EXCLUIR = {k: "Acueducto: " + v for k, v in ACUEDUCTO.items()}
# Por verificar (se mantienen, con nota): centrales menores de la CHEC alrededor de Manizales
VERIFICAR_ACUEDUCTO = {}   # MUNICIPAL: confirmado por Jorge (17-nov-2026) que no es planta de acueducto; se queda en la muestra


def norm(s):
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# 1. Cruce manual de las 60 centrales de 2019 (hoja Mt de DF.xlsx)
#    gen  = nombre en Generacion_Real_2000_2018 (hoja GenM de DF.xlsx)
#    cen  = nombre(s) de planta en Capacidad_CEN.xlsx (sin número de unidad)
#    upme = nombre en Planta_TableToExcel.xls
#    rpe  = nombre en Rio-planta-embalse.xlsx
#    igac = nombre(s) de proyecto en el Reporte de delimitación IGAC
#    sis  = sistema hídrico propuesto (se confirma en T3)
# ---------------------------------------------------------------------------
U = {}  # unidad -> dict


def unidad(uid, nombre, ids, gen=None, cen=(), upme=None, rpe=None, igac=(), sis=None, muestra=1, nota=""):
    U[uid] = dict(unidad=uid, nombre=nombre, ids_2019=list(ids), gen=gen or uid,
                  cen=list(cen) or [uid], upme=upme, rpe=rpe, igac=list(igac),
                  sis=sis or uid, muestra=muestra, nota=nota)


unidad("AGUA FRESCA", "Agua Fresca", ["1AGUA_FRESCA"], upme="AGUA FRESCA", sis="RIO PIEDRAS (JERICO)")
unidad("ALBAN", "Alto y Bajo Anchicayá", ["2ALTO_ANCHICAYA", "5BAJO_ANCHICAYA", "ALBAN"], gen="ALBAN",
       cen=["ALTO ANCHICAYA", "BAJO ANCHICAYA"], upme="ALTO ANCHICAYA", rpe="ALBAN",
       igac=["Alto Anchicaya", "Bajo Anchicaya"], sis="ANCHICAYA",
       nota="XM reporta ALBAN (Alto + Bajo) desde 2000; en 2019 quedaron como dos centrales y Bajo sin generación")
unidad("AMALFI", "Amalfi", ["3AMALFI"], upme="AMALFI")
unidad("ASNAZU", "Asnazú", ["4ASNAZU"], upme="ASNAZU")
unidad("BAYONA", "Bayona", ["6BAYONA"], upme="BAYONA", igac=["Bayona"])
unidad("BELMONTE", "Belmonte", ["7BELMONTE"], upme="BELMONTE")
unidad("BETANIA", "Betania", ["8BETANIA"], upme="BETANIA", rpe="BETANIA", igac=["Betania"], sis="MAGDALENA ALTO")
unidad("CALDERAS", "Calderas", ["9CALDERAS"], upme="CALDERAS MENOR")
unidad("CALIMA", "Calima", ["10CALIMA"], upme="CALIMA", rpe="CALIMA", igac=["Calima"])
unidad("CAMPESTRE (CALARCA)", "Campestre (Calarcá)", ["11CAMPESTRE_CALARCA"], igac=["Campestre (Calarcá)"])
unidad("CHARQUITO", "Charquito", ["12CHARQUITO"], upme="CHARQUITO", igac=["Cadena Río Bogotá"], sis="RIO BOGOTA")
unidad("CHIVOR", "Chivor", ["13CHIVOR"], upme="CHIVOR I y II", rpe="CHIVOR", igac=["Chivor"], sis="BATA")
unidad("COCONUCO", "Coconuco", ["14COCONUCO"], upme="COCONUCO")
unidad("EL BOSQUE", "El Bosque", ["15EL_BOSQUE"], upme="EL BOSQUE")
unidad("EL LIMONAR", "El Limonar", ["16EL_LIMONAR"], upme="EL LIMONAR", igac=["Cadena Río Bogotá"], sis="RIO BOGOTA")
unidad("ESMERALDA", "Esmeralda", ["17ESMERALDA"], upme="ESMERALDA", rpe="ESMERALDA", igac=["Esmeralda"], sis="CHINCHINA")
unidad("GUATAPE", "Guatapé", ["18GUATAPE"], upme="GUATAPE GENERADOR", rpe="GUATAPE", igac=["Guatapé"], sis="NARE-GUATAPE")
unidad("GUAVIO", "Guavio", ["19GUAVIO"], upme="GUAVIO", rpe="GUAVIO", igac=["Guavio"])
unidad("INSULA", "Ínsula", ["20INSULA"], upme="INSULA", igac=["Ínsula"], sis="CHINCHINA")
unidad("IQUIRA I", "Íquira I", ["21IQUIRA_I"], upme="IQUIRA I", sis="IQUIRA")
unidad("IQUIRA II", "Íquira II", ["22IQUIRA_II"], upme="IQUIRA II", sis="IQUIRA")
unidad("JAGUAS", "Jaguas", ["23JAGUAS"], upme="JAGUAS", rpe="JAGUAS", sis="NARE-GUATAPE")
unidad("LA HERRADURA", "La Herradura", ["24LA_HERRADURA"], cen=["LA HERRADURA", "LA HERRADURA 1"],
       upme="MENOR DE LA HERRADURA", igac=["La Herradura"])
unidad("LA TASAJERA", "La Tasajera", ["25LA_TASAJERA"], upme="TASAJERA", rpe="LA TASAJERA", igac=["La Tasajera"], sis="RIO GRANDE")
unidad("LA VUELTA", "La Vuelta", ["26LA_VUELTA"], upme="LA VUELTA", igac=["La Vuelta"])
unidad("MIEL I", "Miel I", ["27MIEL_I"], upme="MIEL 1", rpe="MIEL I", igac=["Miel I"], sis="LA MIEL")
unidad("MIROLINDO", "Mirolindo", ["28MIROLINDO"], upme="MIROLINDO", igac=["Mirolindo"])
unidad("MONDOMO", "Mondomo", ["29MONDOMO"], upme="MONDOMO")
unidad("NIMA", "Nima", ["30NIMA"], upme="NIMA", igac=["Nima I", "Nima II"])
unidad("NIQUIA", "Niquía", ["31NIQUIA"], upme="NIQUIA", igac=["Niquía"], sis="RIO GRANDE")
unidad("PAJARITO", "Pajarito (I + II)", ["32PAJARITO"], upme="PAJARITO", igac=["Pajarito I", "Pajarito II"],
       nota="En 2019 era Pajarito I (4,9 MW); XM hoy reporta PAJARITO = I + II (13,2 MW)")
unidad("PASTALES", "Pastales", ["33PASTALES"], upme="PASTALES", igac=["Pastales"])
unidad("PIEDRAS BLANCAS", "Piedras Blancas", ["34PIEDRAS_BLANCAS"], upme="PIEDRAS BLANCAS", sis="PORCE")
unidad("PLAYAS", "Playas", ["35PLAYAS"], upme="PLAYAS", rpe="PLAYAS", igac=["Playas"], sis="NARE-GUATAPE")
unidad("PORCE II", "Porce II", ["36PORCE_II"], upme="PORCE II", rpe="PORCE II", igac=["Porce II"], sis="PORCE")
unidad("PRADO", "Prado", ["37PRADO"], upme="PRADO GENERADOR", rpe="PRADO", igac=["Prado"], sis="PRADO")
unidad("PRADO IV", "Prado IV", ["38PRADO_IV"], upme="PRADO 4 GENERADOR", igac=["Prado"], sis="PRADO")
unidad("PUENTE GUILLERMO", "Puente Guillermo", ["39PUENTE_GUILLERMO"], upme="PUENTE GUILLRMO")
unidad("RIO BOBO", "Río Bobo", ["40RIO_BOBO"], upme="RIO BOBO", igac=["Río Bobo"])
unidad("RIO CALI", "Río Cali", ["41RIO_CALI"], upme="RIO CALI", igac=["Río Cali I", "Río Cali II"])
unidad("RIO FRIO I", "Río Frío I", ["42RIO_FRIO_I"], upme="RIO FRIO I", igac=["Río Frío I"], sis="RIO FRIO (VALLE)")
unidad("RIO FRIO II", "Río Frío II", ["43RIO_FRIO_II"], upme="RIO FRIO II", sis="RIO FRIO (VALLE)")
unidad("RIO GRANDE", "Río Grande (Mocorongo)", ["44RIO_GRANDE"], cen=["RIO GRANDE"], upme=None,
       igac=["Rio grande – Quebrada Mocorongo"], sis="RIO GRANDE")
unidad("RIO MAYO", "Río Mayo", ["45RIO_MAYO"], cen=["RIOMAYO"], upme="RIO MAYO Generador", igac=["Río Mayo"])
unidad("RIO PALO", "Río Palo", ["46RIO_PALO"], upme="EL PALO", igac=["Río Palo"])
unidad("RIO PIEDRAS", "Río Piedras", ["47RIO_PIEDRAS"], upme="RIO PIEDRAS", igac=["Río Piedras"], sis="RIO PIEDRAS (JERICO)",
       nota="Sitio según UPME: Jericó (Antioquia), Colinversiones/Celsia, 19,9 MW. La hoja DF de 2019 la confundía con Florida II (Cauca). Aguas arriba/abajo de Agua Fresca en el mismo río")
unidad("RIO RECIO", "Río Recio", ["48RIO_RECIO"], upme="RIO RECIO", igac=["Río Recio"])
unidad("RIO SAPUYES", "Río Sapuyes", ["49RIO_SAPUYES"], upme="RIO SANPUYES")
unidad("RIOFRIO (TAMESIS)", "Riofrío (Támesis)", ["50RIOFRIO_TAMESIS"], igac=["Riofrío (Támesis)"])
unidad("RIOGRANDE I", "Riogrande I", ["51RIOGRANDE_I"], upme="RIOGRANDE I", igac=["Riogrande I – Embalse Quebradona"], sis="RIO GRANDE")
unidad("RIONEGRO", "Rionegro", ["52RIONEGRO"], upme="RIONEGRO")
unidad("RUMOR", "Rumor", ["53RUMOR"], upme="RUMOR", igac=["Rumor"])
unidad("SALVAJINA", "Salvajina", ["54SALVAJINA"], upme="SALVAJINA", rpe="SALVAJINA", igac=["Salvajina"], sis="CAUCA ALTO")
unidad("SAN CARLOS", "San Carlos", ["55SAN_CARLOS"], upme="SAN CARLOS I y II", rpe="SAN CARLOS", sis="NARE-GUATAPE")
unidad("SAN FRANCISCO", "San Francisco", ["56SAN_FRANCISCO"], upme="SAN FRANCISCO", rpe="SAN FRANCISCO", igac=["San Francisco"], sis="CHINCHINA")
unidad("SANTA ANA", "Santa Ana", ["57SANTA_ANA"])
unidad("SUEVA 2", "Sueva 2", ["58SUEVA_2"], igac=["Sueva II"])
unidad("TEQUENDAMA", "Tequendama", ["59TEQUENDAMA"], upme="TEQUENDAMA", igac=["Cadena Río Bogotá"], sis="RIO BOGOTA")
unidad("URRA", "Urrá", ["60URRA"], upme="URRA", rpe="URRA", igac=["Urrá"])

# ---------------------------------------------------------------------------
# 2. Centrales fuera de la muestra 2019 con delimitación IGAC ok o Rev (extensión)
# ---------------------------------------------------------------------------
EXT = [
    ("EL QUIMBO", "El Quimbo", ["Quimbo"], "EL QUIMBO", "MAGDALENA ALTO"),
    ("GUATRON", "Guadalupe III + IV + Troneras", ["Guadalupe III", "Guadalupe IV", "Troneras"], "GUATRON", "PORCE"),
    ("ITUANGO", "Ituango", ["Ituango"], None, "CAUCA MEDIO"),
    ("PORCE III", "Porce III", ["Porce III"], "PORCE III", "PORCE"),
    ("PORCE III MENOR", "PCH Porce III", ["PCH Porce III"], None, "PORCE"),
    ("SONSON", "Sonsón", ["Sonsón"], None, None),
    ("CARACOLI", "Caracolí", ["Caracolí"], None, None),
    ("AMOYA LA ESPERANZA", "Amoyá – La Esperanza", ["Amoyá – La Esperanza"], "AMOYA LA ESPERANZA", None),
    ("MANANTIALES", "Minicentral Manantiales", ["Minicentral Manantiales"], None, None),
    ("AYURA", "PCH La Ayurá", ["PCH La Ayurá"], None, "PORCE"),
    ("GUACAICA", "Guacaica", ["Guacaica"], None, "CHINCHINA"),
    ("INTERMEDIA", "Intermedia", ["Intermedia"], None, "CHINCHINA"),
    ("MUNICIPAL", "Municipal", ["Municipal"], None, "CHINCHINA"),
    ("SAN CANCIO", "Sancancio", ["Sancancio"], None, "CHINCHINA"),
    ("TUNJITA", "Tunjita", ["Tunjita"], None, "BATA"),
    ("SOGAMOSO", "Sogamoso", ["Sogamoso"], "SOGAMOSO", None),
    ("PAGUA", "Pagua (Paraíso + La Guaca)", ["Cadena Río Bogotá"], "PAGUA", "RIO BOGOTA"),
    ("AMERICA", "Microcentral América", ["Microcentral América"], None, "PORCE"),
    ("BELLO", "Microcentral Bello", ["Microcentral Bello"], None, "PORCE"),
    ("CAMPESTRE (EPM)", "Microcentral Campestre", ["Microcentral Campestre"], None, "PORCE"),
    ("NUTIBARA", "Microcentral Nutibara", ["Microcentral Nutibara"], None, "PORCE"),
    ("PAT EL DORADO", "PAT El Dorado", ["PAT El Dorado"], None, None),
    ("CASCADA", "La Cascada (ESSA)", ["La Cascada"], None, None),
    ("PALMAS SAN GIL", "Palmas (ESSA)", ["Palmas"], None, None),
    ("NARE", "Nare", ["Nare"], None, None),
    ("ALTO TULUA", "Alto Tuluá", ["Alto Tuluá"], None, "TULUA"),
    ("BAJO TULUA", "Bajo Tuluá", ["Bajo Tuluá"], None, "TULUA"),
    ("AMAIME", "Amaime", ["Amaime"], None, None),
    ("CUCUANA", "Cucuana", ["Cucuana"], "CUCUANA", None),
    ("HIDROMONTAÑITAS", "Hidromontañitas", ["Hidromontañitas"], None, None),
    ("SAN ANDRES", "San Andrés", ["San Andrés"], None, None),
    ("SUEVA I", "Sueva I", ["Sueva I"], None, None),
]
for uid, nom, ig, rpe, sis in EXT:
    unidad(uid, nom, [], rpe=rpe, igac=ig, sis=sis, muestra=0)

# ---------------------------------------------------------------------------
# 3. Lectura de fuentes
# ---------------------------------------------------------------------------
print("Leyendo fuentes…")
DFX = D / "DF.xlsx"
mt = pd.read_excel(DFX, "Mt")
area19 = mt.groupby("id")["Area"].first()
ch2 = pd.read_excel(DFX, "CH2").assign(k=lambda x: x.CH.map(norm)).drop_duplicates("k").set_index("k")
df55 = pd.read_excel(DFX, "DF")
DF55_A_UNIDAD = {"1San_Carlos": "SAN CARLOS", "2GUAVIO": "GUAVIO", "CHIVOR I y II": "CHIVOR", "Hidrosogamoso": "SOGAMOSO",
    "GUATAPE": "GUATAPE", "BETANIA": "BETANIA", "EL QUIMBO": "EL QUIMBO", "PORCE II": "PORCE II", "10MIEL_1": "MIEL I",
    "11ALTO_ANCHICAYA": "ALBAN", "12Urra": "URRA", "13LA_TASAJERA": "LA TASAJERA", "14SALVAJINA": "SALVAJINA",
    "17PLAYAS": "PLAYAS", "18JAGUAS": "JAGUAS", "19SAN_FRANCISCO": "SAN FRANCISCO", "20CALIMA": "CALIMA", "22Amoya": "AMOYA LA ESPERANZA",
    "24PRADO": "PRADO", "26INSULA": "INSULA", "27ESMERALDA": "ESMERALDA", "28CALDERAS_MENOR": "CALDERAS",
    "29PALMAS_SAN_GIL": "PALMAS SAN GIL", "30AMALFI": "AMALFI", "32RIO_MAYO": "RIO MAYO", "33NIQUIA": "NIQUIA",
    "35PIEDRAS_BLANCAS": "PIEDRAS BLANCAS", "38RIO_FRIO_II": "RIO FRIO II", "39IQUIRA_I": "IQUIRA I",
    "41AGUA_FRESCA": "AGUA FRESCA", "42IQUIRA_II": "IQUIRA II", "43PAJARITO": "PAJARITO", "44BELMONTE": "BELMONTE",
    "45PUENTE_GUILLERMO": "PUENTE GUILLERMO", "46RIO_BOBO": "RIO BOBO", "47NIMA": "NIMA", "48RIO_FRIO_I": "RIO FRIO I",
    "49_RIO_SANPUYES": "RIO SAPUYES", "50PASTALES": "PASTALES", "51RIO_CALI": "RIO CALI", "52BAYONA": "BAYONA",
    "53ASNAZU": "ASNAZU", "54RIO_RECIO": "RIO RECIO", "55EL_BOSQUE": "EL BOSQUE",
    "23BAJO_ANCHICAYA": "ALBAN", "15GUADALUPE_III": "GUATRON", "16Guadalupe_IV": "GUATRON", "25Troneras": "GUATRON",
    "Centrales Mayores Bogota": "PAGUA"}
df55["unidad"] = df55.HC.map(DF55_A_UNIDAD)
d55 = df55.dropna(subset=["unidad"]).drop_duplicates("unidad").set_index("unidad")
# Filas de DF (hoja de 55) sin par en la muestra de 60: se reportan como dudosas
df55_sin_par = df55[df55.unidad.isna() | ~df55.unidad.isin([k for k, v in U.items() if v["muestra"]])]
GEN_DESDE = 2000  # primer año del archivo de generación XM

cen = pd.read_excel(CR / "xm_generacion_y_mercado/Capacidad_CEN.xlsx", header=2).iloc[:, 1:].dropna(subset=["Nombre"])
cen = cen.drop_duplicates()
cen["planta"] = cen.Nombre.str.replace(r"\s+\d+$", "", regex=True).str.strip().map(norm)
cenp = cen.groupby("planta").agg(mw=("Capacidad Efectiva Neta [MW]", "sum"),
                                clas=("Clasificación", lambda s: "/".join(sorted(set(s)))),
                                agente=("Opera", "first"))

upme = pd.read_excel(CR / "plantas_hidroelectricas/Planta_TableToExcel.xls")
upme["k"] = upme.PLA_NOMBRE.map(norm)
upme["anio"] = pd.to_datetime(upme.PLA_AÑO_E, errors="coerce")
upme.loc[upme.anio.dt.year < 1890, "anio"] = pd.NaT
upme = upme.sort_values("anio").drop_duplicates("k").set_index("k")
vol_max_col = [c for c in upme.columns if "Volumen" in c and "x" in c][0]

rpe = pd.read_excel(CR / "xm_generacion_y_mercado/Rio-planta-embalse.xlsx", header=4)
rpe.columns = ["planta", "embalse", "rio"]
rpe["planta"] = rpe.planta.ffill()
rpe["embalse"] = rpe.groupby("planta").embalse.transform(lambda s: s.ffill())
rpeg = rpe.dropna(subset=["planta"]).groupby("planta").agg(
    embalse=("embalse", lambda s: "; ".join(dict.fromkeys(s.dropna().astype(str)))),
    rio=("rio", lambda s: "; ".join(dict.fromkeys(s.dropna().astype(str)))))
rpeg.index = rpeg.index.map(norm)

gen_csv = OUT / "generacion_xm_anual_2000_2018.csv"
if not gen_csv.exists():
    print("  agregando generación 2000-2018 (una sola vez)…")
    g = pd.read_excel(CR / "xm_generacion_y_mercado/Generacion_Real_2000_2018.xlsx", header=6)
    g.columns = ["fecha", "planta", "kwh"]
    g["anio"] = pd.to_datetime(g.fecha, errors="coerce").dt.year
    g.groupby(["planta", "anio"]).kwh.sum().div(1e6).round(3).unstack().to_csv(gen_csv)
gen = pd.read_csv(gen_csv, index_col=0)
gen.index = gen.index.map(norm)

pre = pd.read_csv(D / "IGAC_certificados/precarga_proyectos.csv")
pre["k"] = pre.proyecto.map(norm)
deli = pd.read_csv(D / "IGAC_certificados/precarga_delimitaciones.csv").drop_duplicates("proyecto")
deli["k"] = deli.proyecto.map(norm)
rev = pd.read_excel(D / "IGAC_certificados/revision_centrales_xm.xlsx", sheet_name=None, header=0)
rev_enl = pd.concat([rev["Enlazadas"], rev["Por decidir"]], ignore_index=True)
rev_enl["k"] = rev_enl["Proyecto (IGAC)"].map(norm)
rev_enl["codigo"] = rev_enl.get("Código XM").fillna(rev_enl.get("Candidato XM"))
revgen = rev["Generación XM"].set_index("Código")

rep = pd.read_excel(D / "Reporte_Delimitacion_TSE_IGAC_30oct2026.xlsx", "PROYECTOS").iloc[:, :4]
rep = rep.dropna(subset=["PROYECTO"])
rep["k"] = rep.PROYECTO.map(norm)
rep["estado"] = rep.ESTADO.astype(str).str.strip()
rep_idx = rep.set_index("k")

# Listado XM descargado (opcional)
lst_files = sorted((CR / "xm_listado").glob("ListadoRecursos_hidro_*.csv"))
lst = None
if lst_files:
    lst = pd.read_csv(lst_files[-1])
    ccode = next(c for c in lst.columns if c.lower().endswith("code"))
    cname = next(c for c in lst.columns if c.lower().endswith("name"))
    lst["k"] = lst[cname].map(norm)
    print(f"  listado XM: {lst_files[-1].name} ({len(lst)} recursos)")

# ---------------------------------------------------------------------------
# 4. Armado
# ---------------------------------------------------------------------------
dudas = []


def duda(u, tema, detalle, decidir):
    dudas.append(dict(unidad=u, tema=tema, detalle=detalle, que_decidir=decidir, decision=""))


def pick(*vals):
    for v in vals:
        if v is not None and not (isinstance(v, float) and math.isnan(v)) and str(v).strip() not in ("", "nan", "NaT"):
            return v
    return None


def fecha_serial(x):
    try:
        x = float(x)
        return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=x)) if x > 1000 else None
    except Exception:
        return None


filas, comps = [], []
for uid, u in U.items():
    k = norm(uid)
    kg = norm(u["gen"])
    c2 = ch2.loc[kg] if kg in ch2.index else None
    r55 = d55.loc[uid] if uid in d55.index else None

    # --- IGAC
    ig_rows = []
    for p in u["igac"]:
        kp = norm(p)
        est = rep_idx.loc[kp, "estado"] if kp in rep_idx.index else "no figura"
        if isinstance(est, pd.Series):
            est = est.iloc[0]
        def _m(df_):
            ex = df_[df_.k == kp]
            return ex if len(ex) else df_[df_.k.map(lambda x: len(kp) > 5 and (kp in x.split(" ") or x in kp or kp in x)
                                                    and not (x.startswith(kp + " ") and x.split(" ")[len(kp.split(" "))] in ("I", "II", "III", "IV")))]
        pr, dl = _m(pre), _m(deli)
        rv = rev_enl[rev_enl.k == kp]
        ig_rows.append(dict(proyecto=p, estado=est,
                            codigo=pr.codigo_submercado.iloc[0] if len(pr) else (rv.codigo.iloc[0] if len(rv) else None),
                            radicado=dl.radicado.iloc[0] if len(dl) else None,
                            s1=dl.s1_t_declarado.iloc[0] if len(dl) else None,
                            s2=dl.s2_t_declarado.iloc[0] if len(dl) else None))
        comps.append(dict(unidad=uid, componente=p, fuente="Reporte IGAC 30-oct-2026",
                          estado_igac=est, usar_igac=str(est).lower() in ESTADOS_IGAC_VALIDOS,
                          codigo_xm=ig_rows[-1]["codigo"], radicado=ig_rows[-1]["radicado"]))
    for i in u["ids_2019"]:
        comps.append(dict(unidad=uid, componente=i, fuente="DF.xlsx hoja Mt (muestra 2019)"))
    validos = [r for r in ig_rows if str(r["estado"]).lower() in ESTADOS_IGAC_VALIDOS]
    codigos = sorted({r["codigo"] for r in ig_rows if r["codigo"]})

    # --- código XM
    codigo, fcod = (codigos[0], "precarga IGAC") if len(codigos) == 1 else (None, None)
    if len(codigos) > 1:
        duda(uid, "código XM", f"La unidad tiene varios códigos: {codigos}", "Cuál es el código de la unidad")
    if lst is not None:
        m = lst[lst.k.isin({k, kg} | {norm(c) for c in u["cen"]})]
        cods = sorted(set(m[ccode].astype(str)))
        if codigo is None and len(cods) == 1:
            codigo, fcod = cods[0], "ListadoRecursos XM (nombre)"
        elif codigo and cods and codigo not in cods:
            duda(uid, "código XM", f"precarga={codigo}; listado XM por nombre={cods}", "Cuál vale")
        elif codigo is None and len(cods) > 1:
            duda(uid, "código XM", f"Varios recursos XM con el mismo nombre: {cods}", "Cuál es")

    # --- capacidad
    cap_cen = sum(cenp.mw.get(norm(c), 0) for c in u["cen"]) or None
    clas_cen = "/".join(sorted({cenp.clas.get(norm(c)) for c in u["cen"] if norm(c) in cenp.index})) or None
    agente = pick(*[cenp.agente.get(norm(c)) for c in u["cen"]])
    cap25 = revgen["Cap. 2025 (kW)"].get(codigo) / 1000 if codigo in revgen.index else None
    cap19 = pick(r55["CKw"] if r55 is not None else None, c2["TKw"] if c2 is not None else None)
    up = upme.loc[norm(u["upme"])] if u["upme"] and norm(u["upme"]) in upme.index else None

    # --- fecha de entrada
    f_df = r55["YrB"] if r55 is not None else None
    f_ch2 = fecha_serial(c2["Iyear"]) if c2 is not None else None
    f_up = up["anio"] if up is not None else None
    fecha = pick(f_df, f_ch2, f_up)
    ffuente = "DF.xlsx hoja DF" if pick(f_df) else ("DF.xlsx hoja CH2" if pick(f_ch2) else ("UPME Planta" if pick(f_up) else None))
    serie = gen.loc[kg] if kg in gen.index else None
    primer = int(serie[serie > 0].index.astype(int).min()) if serie is not None and (serie > 0).any() else None
    anios_gen = int((serie > 0).sum()) if serie is not None else 0

    # --- tipo
    emb_x = rpeg.embalse.get(norm(u["rpe"])) if u["rpe"] else None
    rio_x = rpeg.rio.get(norm(u["rpe"])) if u["rpe"] else None
    t19 = pick(r55["THC"] if r55 is not None else None, c2["Type"] if c2 is not None else None)
    vmax = up[vol_max_col] if up is not None else None
    votos = {}
    if emb_x:
        votos["XM Río-planta-embalse"] = "filo" if "NO APLICA" in emb_x.upper() else "embalse"
    if clas_cen and "Filo" in clas_cen:
        votos["XM CEN"] = "filo"
    if t19:
        votos["tesis 2019"] = "embalse" if str(t19).lower().startswith("presa") else "filo"
    if pick(vmax) and float(vmax) > 0:
        votos["UPME volumen"] = "embalse"
    tipo = votos.get("XM Río-planta-embalse") or votos.get("XM CEN") or votos.get("tesis 2019")
    if tipo is None and not u["rpe"]:
        tipo = "filo"
        votos["supuesto"] = "filo (no figura en Río-planta-embalse de XM)"
    if len(set(votos.values())) > 1:
        duda(uid, "tipo filo/embalse", "; ".join(f"{a}={b}" for a, b in votos.items()),
             "Filo o embalse (regulación propia)")


    rio = pick(rio_x, r55["Rvr"] if r55 is not None else None, c2["River"] if c2 is not None else None)
    lon = pick(r55["X"] if r55 is not None else None, c2["X"] if c2 is not None else None, up["Lon"] if up is not None else None)
    lat = pick(r55["Y"] if r55 is not None else None, c2["Y"] if c2 is not None else None, up["Lat"] if up is not None else None)
    a19 = sum(area19.get(i, 0) for i in u["ids_2019"] if pick(area19.get(i))) or None

    fila = dict(
        unidad=uid, nombre=u["nombre"], muestra_2019=u["muestra"], ids_2019=";".join(u["ids_2019"]),
        nombre_xm_gen=u["gen"] if serie is not None else None, codigo_xm=codigo, fuente_codigo=fcod, agente=agente,
        cap_efectiva_neta_mw_cen2018=cap_cen, cap_efectiva_neta_mw_2025=cap25, cap_tesis2019_mw=cap19,
        fecha_entrada=pd.to_datetime(fecha).date() if fecha is not None else None, fuente_fecha=ffuente,
        primer_anio_gen_xm=primer, anios_con_gen_2000_2018=anios_gen,
        tipo_propuesto=tipo, fuentes_tipo="; ".join(f"{a}={b}" for a, b in votos.items()),
        embalse_xm=emb_x, rio=rio, sistema_hidrico_propuesto=u["sis"], lon=lon, lat=lat,
        area_cuenca_2019_ha=round(a19, 1) if a19 else None,
        igac_proyectos="; ".join(r["proyecto"] for r in ig_rows),
        igac_estado="; ".join(f'{r["proyecto"]}={r["estado"]}' for r in ig_rows),
        tiene_igac=int(len(validos) > 0),
        igac_radicados="; ".join(r["radicado"] for r in validos if r["radicado"]),
        igac_s1_t_declarado="; ".join(str(r["s1"]) for r in validos if r["s1"]),
        igac_s2_t_declarado="; ".join(str(r["s2"]) for r in validos if r["s2"]),
        nota=u["nota"])
    fila.update(CORRECCIONES.get(uid, {}))
    filas.append(fila)

    # --- reglas de duda
    if u["muestra"] and serie is None:
        duda(uid, "generación XM", f"El nombre '{u['gen']}' no aparece en Generacion_Real_2000_2018", "Nombre XM correcto")
    if fecha is not None and primer and primer > GEN_DESDE and pd.to_datetime(fecha).year < primer - 1:
        duda(uid, "fecha de entrada", f"Fecha registrada {pd.to_datetime(fecha).date()}, pero XM solo tiene generación desde {primer}",
             "Entró en {primer} o XM empezó a reportarla tarde (cambio de nombre, planta menor)".format(primer=primer))
    if fecha is not None and primer and pd.to_datetime(fecha).year > primer + 1:
        duda(uid, "fecha de entrada", f"Fecha registrada {pd.to_datetime(fecha).date()}, pero hay generación XM desde {primer}",
             "Cuál es la fecha real")
    if u["muestra"] and fecha is None and primer and primer > GEN_DESDE:
        duda(uid, "fecha de entrada", f"Sin fecha en fuentes locales; primera generación XM en {primer}",
             "Confirmar con la fecha de operación de ListadoRecursos")
    if a19 and a19 < 1000 and (cap_cen or 0) > 50:
        duda(uid, "cuenca 2019", f"Área 2019 de {a19:,.0f} ha para {cap_cen:g} MW", "Confirma que se rehace (T3)")
    if u["muestra"] and not validos and any(r["estado"] == "N.R." for r in ig_rows):
        pass  # N.R.: no se usa, sin duda
    if u["muestra"] and anios_gen and anios_gen < 10:
        duda(uid, "panel corto", f"Solo {anios_gen} años con generación en 2000-2018 (desde {primer})",
             "Se mantiene en la muestra")

tm = pd.DataFrame(filas)

# --- dudas manuales (revisión de Claude, 17-nov-2026)
duda("ALBAN", "agrupación", "Alto y Bajo Anchicayá: XM solo reporta ALBAN desde feb-2000; en 2019 Alto llevó la generación de ambas y Bajo quedó vacía",
     "Confirmar que se modelan como una unidad (ALBAN) con la cuenca de Bajo Anchicayá (contiene la de Alto)")
duda("RIO PIEDRAS", "cruce de nombres", "La hoja DF de 2019 tiene 'Florida_II' en el río Piedras con coordenadas de Popayán (-76,53; 2,45); XM tiene 'RIO PIEDRAS' (19,9 MW, ~130 GWh/año) y 'RIO PIEDRAS (LA CEJA)'",
     "Ubicación real de la central de la muestra (Celsia Río Piedras) y si la cuenca 2019 se delimitó en el sitio equivocado")
duda("CHIVOR", "sistema hídrico", "En 2019 Chivor quedó en la cadena 'Rio Bogota 2'; Chivor está en el río Batá (embalse La Esperanza/Esmeralda) y no comparte cuenca con el río Bogotá",
     "Confirmar sistema BATA (con Tunjita)")
duda("CHARQUITO", "IGAC cadena", "El IGAC tiene en revisión 'Cadena Río Bogotá' (Enel) como un solo proyecto. Se asignó a Charquito, El Limonar, Tequendama y Pagua",
     "Saber si la delimitación viene por central o una sola para la cadena")
duda("PRADO IV", "agrupación", "Prado IV usa el mismo embalse de Prado y el IGAC tiene un solo proyecto 'Prado'; XM los reporta por separado",
     "Unidad propia con la misma cuenca, o sumar a Prado")
duda("NIQUIA", "tipo", "Niquía turbina agua del acueducto (embalse Riogrande II) y la tesis la marcó 'Presa'",
     "Embalse (comparte Riogrande II con La Tasajera) o filo")
duda("SAN CARLOS", "IGAC", "San Carlos (1.240 MW, ISAGEN) no figura en el reporte del IGAC; tampoco Jaguas. Es la central con la peor cuenca de 2019 (178 ha)",
     "Si ISAGEN ya radicó o si toca delimitarla con DEM")
duda("JAGUAS", "IGAC", "Jaguas (ISAGEN) no figura en el reporte del IGAC", "Delimitar con DEM")
duda("CASCADA", "cruce de nombres", "IGAC 'La Cascada' (ESSA). XM tiene 'CASCADA' (3 MW), 'LA CASCADA (ANTIOQUIA)' y 'LA CASCADA ( ABEJORRAL)'", "Cuál es la de ESSA")
duda("NARE", "cruce de nombres", "IGAC 'Nare' (empresa NARE). En XM solo aparece 'CEMENTOS DEL NARE' (4,5 MW)", "Recurso XM que corresponde")
duda("PAT EL DORADO", "cruce de nombres", "Proyecto IGAC de EPM sin nombre equivalente en los archivos XM locales", "Nombre o código XM")
_sp = df55_sin_par[df55_sin_par.HC != "23BAJO_ANCHICAYA"]
duda("(muestra)", "muestra 2019", "La hoja DF de DF.xlsx (55 centrales, muestra anterior) trae " + str(len(_sp)) +
     " que no están en las 60 del panel (hoja Mt): " + "; ".join(f"{r.HC} ({r.CKw:g} MW)" for _, r in _sp.iterrows()),
     "Confirmar que la réplica usa solo las 60 de Mt (Sogamoso, Quimbo, Guatron y Amoyá quedan como extensión)")
duda("CHARQUITO", "tipo", "Charquito, El Limonar y Tequendama son a filo pero aguas abajo del embalse del Muña y del agregado Bogotá",
     "Filo (como en 2019) con nota de regulación aguas arriba")
duda("RIOGRANDE I", "tipo", "No figura con embalse en XM, pero el IGAC la delimitó como 'Embalse Quebradona'", "Filo o embalse")
duda("SANTA ANA", "sistema hídrico", "Santa Ana (Enel, 8 MW) y Rionegro (Enel, 10,2 MW) no tienen río ni sistema en las fuentes locales",
     "Río de cada una y si pertenecen al sistema río Bogotá")


# ---------------------------------------------------------------------------
# 5. Series de XM procesadas localmente (02_datos/xm_procesado, ver procesar_xm_local.py)
#    Capacidad efectiva neta diaria 2007-2024 y generación horaria 2000-2024.
#    Decisión de Jorge (17-nov-2026): capacidad = la de XM, promedio del año.
# ---------------------------------------------------------------------------
XP = D / "xm_procesado"
XM_REC = {  # unidad -> recursos XM que se suman (cambios de nombre o reporte separado)
    "ALBAN": ["ALBAN", "ALTO ANCHICAYA", "BAJO ANCHICAYA"],
    "TEQUENDAMA": ["TEQUENDAMA", "TEQUENDAMA 1", "TEQUENDAMA 2", "TEQUENDAMA 3", "TEQUENDAMA 4"],
    "AMOYA LA ESPERANZA": ["AMOYA", "AMOYA LA ESPERANZA"],
    "AYURA": ["AYURA", "AUTOG AYURA"],
    "NARE": ["CEMENTOS DEL NARE", "AUTG CEMENTOS DEL NARE", "AUTOG CEMENTOS DEL NARE"],
    "SAN ANDRES": ["SAN ANDRES DE CUERQUIA"],
}
if (XP / "recursos_hidro.csv").exists():
    print("Integrando series XM locales…")
    rec = pd.read_csv(XP / "recursos_hidro.csv").set_index("recurso")
    capd = pd.read_csv(XP / "capacidad_hidro_diaria.csv.gz", parse_dates=["fecha"])
    gend = pd.read_csv(XP / "generacion_hidro_diaria.csv.gz", parse_dates=["fecha"], usecols=["fecha", "recurso", "kwh", "kwh_hora_max"])
    camb = pd.read_csv(XP / "cambios_capacidad_xm.csv", parse_dates=["fecha"])
    panel, cambios_u, mapa = [], [], []
    # días en que XM empezó a reportar muchos recursos a la vez: el "primer día con generación" ahí
    # refleja el inicio del reporte (plantas menores), no la entrada en operación
    _ini = gend[gend.kwh > 0].groupby("recurso").fecha.min()
    DIAS_MASIVOS = set(_ini.value_counts()[lambda x: x >= 4].index)
    for i, f in tm.iterrows():
        uid = f.unidad
        nombres = XM_REC.get(uid) or [n for n in [f.nombre_xm_gen, uid] if isinstance(n, str) and n in rec.index][:1]
        nombres = [n for n in nombres if n in rec.index]
        if not nombres:
            continue
        for n in nombres:
            mapa.append(dict(unidad=uid, recurso_xm=n, codigo=rec.codigo.get(n), gen_desde=rec.gen_desde.get(n), gen_hasta=rec.gen_hasta.get(n)))
        cods = sorted({str(rec.codigo.get(n)) for n in nombres if pd.notna(rec.codigo.get(n))})
        if pd.isna(f.codigo_xm) and cods:
            tm.at[i, "codigo_xm"] = "; ".join(cods)
            tm.at[i, "fuente_codigo"] = "XM Generación 2024 (Código Recurso)"
        elif pd.notna(f.codigo_xm) and cods and f.codigo_xm not in cods:
            duda(uid, "código XM", f"precarga={f.codigo_xm}; XM 2024={cods}", "Cuál vale")
        # capacidad diaria de la unidad = suma de sus recursos ese día
        cu = capd[capd.recurso.isin(nombres)].groupby("fecha").kw.sum().div(1000)
        gu = gend[gend.recurso.isin(nombres)].groupby("fecha").agg(kwh=("kwh", "sum"), hmax=("kwh_hora_max", "sum"))
        if len(cu):
            tm.at[i, "cap_xm_mw_2024"] = round(cu.iloc[-1], 3) if cu.index[-1].year == 2024 else None
            tm.at[i, "cap_xm_mw_primera"] = round(cu.iloc[0], 3)
            # cambios persistentes (el nuevo valor dura al menos 30 días)
            s_ = cu.round(3)
            bloques = (s_ != s_.shift()).cumsum()
            runs = s_.groupby(bloques).agg(["first", "size"]).assign(fecha=s_.groupby(bloques).apply(lambda x: x.index[0]))
            runs = runs[runs["size"] >= 30]
            runs = runs[runs["first"] != runs["first"].shift()]
            for (_, r0), (_, r1) in zip(runs.iloc[:-1].iterrows(), runs.iloc[1:].iterrows()):
                cambios_u.append(dict(unidad=uid, fecha=r1.fecha.date(), mw_antes=r0["first"], mw_despues=r1["first"],
                                      tipo="aumento" if r1["first"] > r0["first"] else "reducción"))
            tm.at[i, "cambios_capacidad_xm"] = "; ".join(f'{c["fecha"]}: {c["mw_antes"]:g}→{c["mw_despues"]:g} MW'
                                                          for c in cambios_u if c["unidad"] == uid)
        pos = gu[gu.kwh > 0]
        if len(pos):
            f0 = pos.index.min()
            tm.at[i, "inicio_gen_xm"] = f0.date()
            tm.at[i, "fin_gen_xm"] = pos.index.max().date()
            # decisión Jorge: fecha de entrada = inicio de generación en XM (si empieza en ene-2000 es anterior al registro)
            if f0 in DIAS_MASIVOS or f0 <= pd.Timestamp("2000-12-31"):
                tm.at[i, "fecha_entrada"] = f"{f0.date()} o antes"
                tm.at[i, "fuente_fecha"] = "XM: inicio de reporte (ese día XM empezó a reportar varias plantas); la entrada real puede ser anterior"
            elif f0 > pd.Timestamp("2000-01-31"):
                tm.at[i, "fecha_entrada"] = f0.date()
                tm.at[i, "fuente_fecha"] = "XM: primer día con generación"
            elif pd.notna(f.fecha_entrada) and pd.to_datetime(f.fecha_entrada) < pd.Timestamp("2000-01-01"):
                tm.at[i, "fuente_fecha"] = (f.fuente_fecha or "") + " (anterior a 2000; XM genera desde ene-2000)"
            else:
                tm.at[i, "fecha_entrada"] = "anterior a 2000"
                tm.at[i, "fuente_fecha"] = "XM genera desde ene-2000; fecha registrada posterior era errada" if pd.notna(f.fecha_entrada) else "XM genera desde ene-2000"
            if pos.index.max() < pd.Timestamp("2024-06-30"):
                tm.at[i, "anio_fin_panel"] = pos.index.max().year
        anios = sorted(set(gu.index.year) | set(cu.index.year))
        prim_cap = cu.iloc[0] if len(cu) else None
        for a in anios:
            ga = gu[gu.index.year == a]
            ca = cu[cu.index.year == a]
            horas = 8784 if pd.Timestamp(a, 12, 31).dayofyear == 366 else 8760
            if len(ca) >= 300:
                cap_a, fte = ca.mean(), "XM CEN diaria"
            elif len(ca):
                cap_a, fte = ca.mean(), f"XM CEN ({len(ca)} días)"
            elif prim_cap is not None and a < cu.index[0].year:
                cap_a, fte = prim_cap, "XM primer valor (2007) hacia atrás"
            else:
                cap_a, fte = None, None
            gwh = ga.kwh.sum() / 1e6 if len(ga) else None
            p99 = ga.hmax.quantile(0.99) / 1000 if len(ga) else None
            # capacidad ajustada: si la generación horaria (percentil 99) supera la declarada, manda la observada
            cap_aj = max(cap_a, p99) if cap_a and p99 and p99 > cap_a * 1.05 else cap_a
            panel.append(dict(unidad=uid, anio=a, gen_gwh=gwh, dias_gen=len(ga), cap_mw=cap_a, fuente_cap=fte,
                              cap_obs_p99_mw=p99, cap_mw_ajustada=cap_aj,
                              fc=(gwh * 1000 / (cap_a * horas)) if gwh is not None and cap_a else None,
                              fc_ajustado=(gwh * 1000 / (cap_aj * horas)) if gwh is not None and cap_aj else None))
    pan = pd.DataFrame(panel)
    pan["fc_mayor_1"] = (pan.fc > 1).astype(int)   # decisión Jorge: se le cree a la generación; nota en el paper
    pan.round(4).to_csv(OUT / "panel_xm_unidad_anio.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cambios_u).to_csv(OUT / "cambios_capacidad_unidad.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(mapa).to_csv(OUT / "unidad_recursos_xm.csv", index=False, encoding="utf-8-sig")
    # promedio 2001-2015 para comparar con la tesis 2019
    m15 = pan[pan.anio.between(2001, 2015)].groupby("unidad").cap_mw.mean()
    tm["cap_xm_mw_prom_2001_2015"] = tm.unidad.map(m15).round(2)
    # dudas que solo XM puede resolver
    for uid, g in pan.groupby("unidad"):
        if not tm.loc[tm.unidad == uid, "muestra_2019"].iloc[0]:
            continue
        malo = g[(g.fc > 1) | ((g.cap_obs_p99_mw > 1.25 * g.cap_mw) & (g.anio < 2007))]
        if len(malo):
            duda(uid, "capacidad (XM)", "Años con FC>1 o generación horaria muy por encima de la capacidad: " +
                 ", ".join(f"{int(r.anio)} (FC={r.fc:.2f}, máx. hora p99={r.cap_obs_p99_mw:.1f} MW, cap={r.cap_mw:.1f})" for _, r in malo.iterrows()),
                 "Capacidad real en esos años (posible subdeclaración o cambio no registrado)")
        sin = g[g.gen_gwh.notna() & g.cap_mw.isna()]
        if len(sin):
            duda(uid, "capacidad (XM)", f"Años con generación y sin capacidad: {sorted(sin.anio.astype(int).tolist())}", "Qué capacidad usar")
        fin = g[g.gen_gwh.fillna(0) > 0].anio.max()
        if fin < 2015:
            duda(uid, "panel corto", f"Deja de generar en XM en {int(fin)}", "Sale del panel desde ese año (se confirma retiro)")
    # la capacidad de la tesis 2019 queda como referencia, no como duda
    dif = (tm.cap_tesis2019_mw - tm.cap_xm_mw_prom_2001_2015).abs() / tm.cap_xm_mw_prom_2001_2015
    tm["cap_tesis2019_error"] = (dif > 0.2).map({True: "sí", False: ""})

tm["incluir_analisis"] = (~tm.unidad.isin(EXCLUIR)).astype(int)
tm["motivo_exclusion"] = tm.unidad.map(EXCLUIR)
tm["acueducto"] = tm.unidad.map(lambda u: "sí" if u in ACUEDUCTO else ("verificar" if u in VERIFICAR_ACUEDUCTO else ""))
tm["nota_acueducto"] = tm.unidad.map({**ACUEDUCTO, **VERIFICAR_ACUEDUCTO})
# Decisión de Jorge (17-nov-2026): la muestra principal son las unidades con delimitación IGAC en estado "ok".
# Se amplía sola: cuando un proyecto pase de "Rev" a "ok" en el reporte del IGAC, entra al volver a correr.
tm["igac_ok"] = tm.igac_estado.fillna("").str.contains(r"=ok\b", case=False).astype(int)
tm["igac_en_cola"] = (~tm.igac_ok.astype(bool) & tm.igac_estado.fillna("").str.contains(r"=Rev\b")).astype(int)
tm["muestra_principal"] = ((tm.igac_ok == 1) & (tm.incluir_analisis == 1)).astype(int)
nfc = pan[pan.fc > 1].groupby("unidad").anio.apply(lambda x: ", ".join(str(int(a)) for a in x)) if "pan" in dir() else {}
tm["anios_fc_mayor_1"] = tm.unidad.map(nfc)
dd = pd.DataFrame(dudas).drop_duplicates(["unidad", "tema", "detalle"])
DECF = OUT / "decisiones_jorge.csv"
if DECF.exists():
    dec = pd.read_csv(DECF, sep=";").drop_duplicates(["unidad", "tema"], keep="last")
    dd = dd.drop(columns="decision").merge(dec[["unidad", "tema", "decision"]], on=["unidad", "tema"], how="left")
dd["estado"] = dd.decision.notna().map({True: "resuelto", False: "pendiente"})
# lo que queda en espera de terceros (IGAC) se marca aparte
espera = dd.decision.fillna("").str.contains("espera|esperar|revisar con la cuenca IGAC", case=False)
dd.loc[espera, "estado"] = "en espera (IGAC)"
dd = dd.sort_values(["estado", "unidad"], key=lambda c: c.map({"pendiente": 0, "en espera (IGAC)": 1, "resuelto": 2}) if c.name == "estado" else c)
tm.to_csv(OUT / "tabla_maestra.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(comps).to_csv(OUT / "componentes.csv", index=False, encoding="utf-8-sig")
dd.to_csv(OUT / "casos_dudosos.csv", index=False, encoding="utf-8-sig", sep=";")   # ';' para que Excel en español lo abra bien
try:
    dd.to_excel(OUT / "casos_dudosos.xlsx", index=False)
except Exception as e:
    print("  (sin xlsx:", e, ")")
print(f"tabla_maestra.csv: {len(tm)} unidades · muestra principal (IGAC ok, sin acueducto): {tm.muestra_principal.sum()} · en cola (Rev): {tm.igac_en_cola.sum()}")
print(f"  con código XM: {tm.codigo_xm.notna().sum()} · con IGAC ok/Rev: {tm.tiene_igac.sum()}")
print(f"casos_dudosos: {len(dd)} casos · " + ", ".join(f"{k}={v}" for k, v in dd.estado.value_counts().items()))
