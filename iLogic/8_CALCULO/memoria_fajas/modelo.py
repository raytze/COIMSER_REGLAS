"""PASO 2 - Lectura del XML del generador de correas trapezoidales (Design Accelerator).

El XML vive en la ocurrencia del ensamble: AttributeSets['FDesign']['Data'], clase CAVBelts.
Los valores estan en unidades internas de Inventor (cm, kg, s, rad); el atributo Units
es la unidad de VISUALIZACION y aqui se convierte a ella:
    P  = 1e8      kg*cm2/s3  -> 10 kW
    n  = 151.84   rad/s      -> 1450 rpm
    T  = 658572   kg*cm2/s2  -> 65.86 N*m
    F  = 87054.8  kg*cm/s2   -> 870.55 N
Cada parametro queda como {"valor", "unidad", "min", "max", "desc"}. Min/Max son los
limites que usa el propio Design Accelerator en su comprobacion (Cpr >= 1.2, v <= 30.48 m/s...).
"""
import math
import xml.etree.ElementTree as ET

# unidad de visualizacion -> (factor desde interno, unidad normalizada)
FACTORES = {
    "mm": (10.0, "mm"), "cm": (1.0, "cm"), "m": (0.01, "m"), "in": (1 / 2.54, "in"),
    "deg": (180.0 / math.pi, "deg"), "rad": (1.0, "rad"), "rpm": (60.0 / (2 * math.pi), "rpm"),
    "kW": (1e-7, "kW"), "W": (1e-4, "W"), "hp": (1e-4 / 745.6999, "hp"),
    "m N": (1e-4, "N·m"), "N m": (1e-4, "N·m"), "N": (0.01, "N"), "mps": (0.01, "m/s"),
    "kg/m": (100.0, "kg/m"), "Hz": (1.0, "Hz"), "s/m": (100.0, "s/m"), "ul": (1.0, ""), "": (1.0, ""),
}

DESC = {
    # transmision
    "nb": "Número de correas", "Zofst": "Desfase en Z del plano medio",
    # correa
    "fmax": "Frecuencia máxima de flexión admisible", "v": "Velocidad de la correa",
    "SpcMass": "Masa por unidad de longitud", "Alfa": "Ángulo de la correa / ranura",
    "H": "Altura de la correa", "Hw": "Altura hasta línea primitiva",
    "a": "Distancia de la línea primitiva", "Bw": "Ancho primitivo", "B": "Ancho superior",
    "Lw": "Longitud primitiva (de referencia)", "Li": "Longitud interior", "Le": "Longitud exterior",
    "Dwmin": "Diámetro primitivo mínimo de polea", "PRB": "Potencia básica por correa",
    "C3": "Factor de longitud de correa", "Dpc": "Corrección de diámetro", "Nc": "Velocidad de corrección",
    # polea
    "Beta": "Ángulo de contacto", "X": "Coordenada X del centro", "Y": "Coordenada Y del centro",
    "C": "Distancia entre centros", "Lf": "Longitud del ramal libre",
    "Dp": "Diámetro exterior / efectivo", "Dw": "Diámetro primitivo", "Px": "Participación de potencia",
    "i": "Relación de transmisión real", "iD": "Relación de transmisión geométrica",
    "i_t": "Relación teórica", "Speed": "Velocidad de giro", "P": "Potencia", "T": "Par torsor",
    "Fv": "Fuerza en la línea de centros", "F1": "Tensión ramal tenso", "F2": "Tensión ramal flojo",
    "Fr": "Fuerza radial resultante sobre el eje", "c": "Profundidad sobre línea primitiva",
    "Hd": "Profundidad de ranura", "ng": "Número de ranuras", "Se": "Distancia al borde",
    "Sg": "Paso entre ranuras", "r1": "Radio 1", "r2": "Radio 2", "fg": "Coeficiente de rozamiento",
    # calculo
    "C1": "Factor de ángulo de contacto", "C2": "Factor de servicio",
    "C4": "Factor de corrección C4", "C5": "Factor de corrección C5",
    "Cpr": "Factor de seguridad de potencia", "fb": "Frecuencia de flexión",
    "zer": "Número de correas requerido", "fMod": "Módulo de frecuencia",
    "Fp": "Fuerza periférica (útil)", "Fc": "Fuerza centrífuga",
    "Ft": "Tensión de montaje por correa", "FtMax": "Tensión máxima por correa",
    "eff": "Eficiencia de la transmisión", "effT": "Eficiencia teórica de la correa",
    "k1": "Factor de pretensión", "s": "Deslizamiento",
}


def convertir(valor_interno, unidad):
    if unidad not in FACTORES:
        raise KeyError(f"Unidad no soportada en el XML: {unidad!r} (agregar en modelo.FACTORES)")
    f, u = FACTORES[unidad]
    return valor_interno * f, u


def _limite(e, k, u):
    if e.get(k) is None:
        return None
    x = float(e.get(k))
    return None if abs(x) >= 1e9 else convertir(x, u)[0]   # 1e10 = sin limite


def _param(e):
    u = e.get("Units", "")
    val, un = convertir(float(e.get("Val")), u)
    return {"valor": val, "unidad": un, "min": _limite(e, "Min", u), "max": _limite(e, "Max", u),
            "desc": DESC.get(e.tag, "")}


def _params(nodo):
    return {c.tag: _param(c) for c in nodo if c.get("Val") is not None}


def leer_xml(xml, nombre="Transmision"):
    """xml: bytes (UTF-16 con BOM, como lo escribe la regla) o str."""
    if isinstance(xml, str):
        xml = xml.encode("utf-16") if 'encoding="UTF-16"' in xml[:80] else xml.encode("utf-8")
    root = ET.fromstring(xml)
    obj = root.find("Object")
    if obj is None or obj.get("Class") != "CAVBelts":
        raise RuntimeError("El XML no es de una transmisión por correa trapezoidal (CAVBelts).")
    belt = obj.find("Path/Belt")
    poleas = []
    for p in obj.find("Path/Pulleys"):
        poleas.append({"posicion": int(p.get("ePlace")), "designacion": p.get("SizeDsn"),
                       "familia_ranura": p.get("CFFamily"), "id": p.get("IntName"),
                       "parametros": _params(p)})
    poleas.sort(key=lambda x: x["posicion"])
    pmax = max(poleas, key=lambda x: x["parametros"]["P"]["valor"])
    for p in poleas:
        p["motriz"] = p is pmax
    pw = belt.find("Power")
    return {
        "nombre": nombre, "id": obj.get("IntName"), "generador": obj.get("Class"),
        "transmision": _params(obj.find("Path")),
        "correa": {"designacion": belt.get("SizeDsn"), "codigo": belt.get("CFMoniker"),
                   "familia": belt.get("CFFamily"),
                   "formula_potencia": pw.get("Formula") if pw is not None else None,
                   "parametros": _params(belt)},
        "poleas": poleas,
        "calculo": _params(obj.find("Calc")),
    }
