import re
"""Lectura del XML 'FDesign' del Shaft Generator de Inventor (Design Accelerator).

El XML guarda los valores en unidades internas de Inventor (cm, kg, s, rad).
Todo se convierte aquí a: mm, N, N·mm, MPa (N/mm²), kg/m³, grados.

Las posiciones de apoyos, cargas y operaciones son RELATIVAS a un punto de
referencia ('HotSpot') de un tramo: inicio, mitad o fin. Se resuelven a x absoluta.
"""
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# Conversión de unidades internas -> unidades de trabajo, según el atributo Units
_CONV = {
    "mm": 10.0,            # cm -> mm
    "N": 0.01,             # kg·cm/s² -> N
    "m N": 1e-4 * 1000.0,  # kg·cm²/s² -> N·m -> N·mm
    "MPa": 1e-4,           # kg/(cm·s²) -> MPa
    "kg/m^3": 1e6,         # kg/cm³ -> kg/m³
    "N/mm": 1e-3,          # kg/s² (N/m) -> N/mm
    "microm": 1e4,         # cm -> µm
    "microm/N": 1e3,       # cm/(kg·cm/s²) -> mm/N (flexibilidad de apoyo)
    "deg": 180.0 / math.pi,  # rad -> grados
    "ul": 1.0, "su": 1.0, "kg": 1.0,
}


def _v(parent, tag, default=None):
    """Valor convertido del hijo <tag Val=.. Units=..>."""
    if parent is None:
        return default
    e = parent.find(tag)
    if e is None or e.get("Val") is None:
        return default
    val = float(e.get("Val"))
    return val * _CONV.get(e.get("Units", "ul"), 1.0)


@dataclass
class Tramo:
    idx: int
    tipo: str          # Cilindro, Cono, ...
    x0: float          # mm
    L: float           # mm
    D1: float          # mm (izquierda)
    D2: float          # mm (derecha; = D1 en cilindro)
    clase: str = ""

    @property
    def x1(self):
        return self.x0 + self.L

    def D(self, x):
        if self.L <= 0:
            return self.D1
        t = min(max((x - self.x0) / self.L, 0.0), 1.0)
        return self.D1 + (self.D2 - self.D1) * t


@dataclass
class Operacion:      # chaflán, empalme, chavetero, ranura, rosca...
    tipo: str
    clase: str
    tramo: int
    lado: str          # izq / der / medio
    x0: float          # mm absoluta
    x1: float
    R: float = 0.0     # radio de empalme (mm)
    params: dict = field(default_factory=dict)  # parametros numericos leidos del XML (mm / deg)
    prof: float = 0.0  # profundidad de ranura/desahogo leida de Inventor (mm); 0 = no disponible
    desig: str = ""    # designacion de rosca (ThreadDesignation), p. ej. TR14x2


@dataclass
class Apoyo:
    x: float
    fijo_axial: bool
    F_inv: float = 0.0     # reacción calculada por Inventor (N)
    rot_inv: float = 0.0   # giro en el apoyo según Inventor (°)
    cy: float = 0.0        # flexibilidad del apoyo en el plano XY (mm/N); 0 = rígido
    cz: float = 0.0        # flexibilidad del apoyo en el plano XZ (mm/N)


@dataclass
class Carga:
    x: float
    Fy: float = 0.0
    Fz: float = 0.0
    Fx: float = 0.0        # axial
    My: float = 0.0        # momento flector (plano XY) N·mm
    Mz: float = 0.0        # momento flector (plano XZ) N·mm
    T: float = 0.0         # torsor N·mm
    qy: float = 0.0        # carga distribuida N/mm
    qz: float = 0.0
    Lq: float = 0.0        # longitud de la carga distribuida (mm)
    tipo_inv: str = ""


@dataclass
class Material:
    nombre: str
    E: float
    G: float
    nu: float
    Sy: float
    Su: float
    rho: float


@dataclass
class ResultadosInventor:
    masa: float = 0.0          # kg
    sigma_max: float = 0.0     # MPa (flexión)
    tau_max: float = 0.0       # MPa (corte)
    tors_max: float = 0.0      # MPa
    tens_max: float = 0.0      # MPa
    red_max: float = 0.0       # MPa (esfuerzo reducido)
    flecha_max: float = 0.0    # µm
    giro_tors: float = 0.0     # °


@dataclass
class Eje:
    nombre: str
    tramos: list
    huecos: list               # tramos de agujero (Tramo) con x absoluta
    operaciones: list
    apoyos: list
    cargas: list
    material: Material
    usa_peso: bool
    inv: ResultadosInventor
    beta: float = 0.0
    usa_beta: bool = False
    avisos: list = field(default_factory=list)

    @property
    def longitud(self):
        return self.tramos[-1].x1 if self.tramos else 0.0

    def tramo_en(self, x):
        for t in self.tramos:
            if t.x0 - 1e-9 <= x <= t.x1 + 1e-9:
                return t
        return self.tramos[-1]

    def D(self, x):
        return self.tramo_en(x).D(x)

    def di(self, x):
        for h in self.huecos:
            if h.x0 - 1e-9 <= x <= h.x1 + 1e-9:
                return h.D(x)
        return 0.0


_TIPO_TRAMO = {"cylinder": "Cilindro", "cone": "Cono", "polygon": "Polígono"}


def _tipo_tramo(clase):
    c = clase.lower()
    for k, v in _TIPO_TRAMO.items():
        if k in c:
            return v
    return clase.replace("CPShaftElement", "")


def _diametros(obj):
    """Devuelve (D1, D2) de un tramo, sea cilindro o cono."""
    D = _v(obj, "D")
    if D is not None:
        return D, D
    D1 = _v(obj, "D1")
    D2 = _v(obj, "D2")
    if D1 is not None:
        return D1, (D2 if D2 is not None else D1)
    # último recurso: el primer hijo con unidades mm que empiece con D
    for e in obj:
        if e.tag.startswith("D") and e.get("Units") == "mm":
            d = float(e.get("Val")) * 10.0
            return d, d
    return 0.0, 0.0


def _tipo_operacion(clase):
    c = clase.lower()
    if "fillet" in c:
        return "Empalme"
    if "chamfer" in c:
        return "Chaflán"
    if "key" in c:
        return "Chavetero"
    if "thread" in c:
        return "Rosca"
    if "groove" in c or "ring" in c or "relief" in c:
        return "Ranura"
    if "neck" in c or "notch" in c:
        return "Desahogo"
    if "hole" in c:
        return "Agujero"
    if "wrench" in c:
        return "Plano"
    return clase.replace("CPShaftFeature", "")


def _leer_tramos(lista, hot, x_inicio, desde_derecha=False, L_total=0.0, prefijo=""):
    tramos = []
    x = x_inicio
    if lista is None:
        return tramos
    for i, obj in enumerate(lista.findall("Object"), 1):
        L = _v(obj, "Length", 0.0)
        D1, D2 = _diametros(obj)
        if desde_derecha:
            x0 = L_total - (x + L)
            t = Tramo(i, _tipo_tramo(obj.get("Class", "")), x0, L, D2, D1, obj.get("Class", ""))
        else:
            t = Tramo(i, _tipo_tramo(obj.get("Class", "")), x, L, D1, D2, obj.get("Class", ""))
        for tag, pos in (("HotSpot_Start", t.x0), ("HotSpot_End", t.x1), ("HotSpot_Middle", t.x0 + L / 2)):
            e = obj.find(tag)
            if e is not None and e.get("IntName"):
                hot[e.get("IntName")] = pos
        tramos.append((t, obj))
        x += L
    return tramos


def leer_xml(texto, nombre="Eje"):
    if isinstance(texto, bytes):
        if texto[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(texto) > 1 and texto[1:2] == b"\x00"):
            texto = texto.decode("utf-16")
        else:
            texto = texto.decode("utf-8-sig", errors="replace")
    # se quita la declaracion de codificacion (el texto ya esta decodificado)
    texto = re.sub(r"^\s*<\?xml[^>]*\?>", "", texto)
    root = ET.fromstring(texto)
    sh = root.find("Object")
    if sh is None:
        sh = root.find("Template")  # formato FDesign/Template (otras versiones)
        if sh is not None and root.get("ClassName") == "CAShaft":
            sh.set("Class", "CAShaft")
    if sh is None or sh.get("Class") != "CAShaft":
        raise ValueError("El XML no corresponde a un eje del Shaft Generator (CAShaft).")
    comp = sh.find("ShaftComponent")
    hot = {}
    avisos = []

    tr = _leer_tramos(comp.find("ElementsShaft"), hot, 0.0)
    tramos = [t for t, _ in tr]
    L_total = tramos[-1].x1 if tramos else 0.0

    huecos = [t for t, _ in _leer_tramos(comp.find("ElementsHollowLeft"), hot, 0.0)]
    huecos += [t for t, _ in _leer_tramos(comp.find("ElementsHollowRight"), hot, 0.0, True, L_total)]

    # Operaciones en los agujeros (roscas internas, chaveteros...): no se evaluan; se avisa
    for tag in ("ElementsHollowLeft", "ElementsHollowRight"):
        sec = comp.find(tag)
        if sec is None:
            continue
        for f in sec.iter("Object"):
            c_ = f.get("Class", "")
            if "Thread" in c_:
                avisos.append(f"Rosca en el agujero del eje ({f.get('ThreadDesignation', c_)}): no se evalúa su concentrador de "
                              "esfuerzos ni el diámetro de núcleo; verificarla aparte.")
    # Operaciones (empalmes, chaveteros...)
    ops = []
    for t, obj in tr:
        for tag, lado in (("Features_Left", "izq"), ("Features_Right", "der"), ("Features", "medio")):
            lst = obj.find(tag)
            if lst is None:
                continue
            for f in lst.findall("Object"):
                clase = f.get("Class", "")
                tipo = _tipo_operacion(clase)
                xr = _v(f, "x", 0.0)
                Lf = _v(f, "L", None)
                if Lf is None or tipo in ("Chaflán", "Empalme"):
                    Lf = 0.0 if tipo in ("Chaflán", "Empalme") else (_v(f, "Length", 0.0) or 0.0)
                # ancho y profundidad reales (Length es solo la zona disponible)
                prof = 0.0
                if tipo == "Ranura" and f.find("M") is not None:
                    Lf = _v(f, "M", 0.0) or Lf
                    d1 = _v(f, "D1", 0.0) or 0.0
                    if 0 < d1 < t.D(t.x0):
                        prof = (t.D(t.x0) - d1) / 2
                elif tipo == "Desahogo" and f.find("b") is not None:
                    Lf = _v(f, "b", 0.0) or Lf
                    prof = _v(f, "h", 0.0) or 0.0
                if lado == "der":
                    x1 = t.x1 - xr
                    x0 = x1 - Lf
                else:
                    x0 = t.x0 + xr
                    x1 = x0 + Lf
                op = Operacion(tipo, clase, t.idx, lado, x0, x1, _v(f, "R", 0.0) or 0.0, prof=prof,
                               desig=f.get("ThreadDesignation", ""))
                for ch in f:
                    if ch.get("Val") is not None and ch.get("Units") in ("mm", "deg"):
                        try:
                            op.params[ch.tag] = _v(f, ch.tag, 0.0)
                        except ValueError:
                            pass
                ops.append(op)
                for tg, pos in (("HotSpot_Start", x0), ("HotSpot_End", x1), ("HotSpot_Middle", (x0 + x1) / 2)):
                    e = f.find(tg)
                    if e is not None and e.get("IntName"):
                        hot[e.get("IntName")] = pos
                if tipo not in ("Chaflán", "Empalme", "Chavetero", "Ranura", "Rosca", "Desahogo"):
                    avisos.append(f"Operación no reconocida en el tramo {t.idx}: {clase}. No se considera en el cálculo.")

    def x_abs(obj):
        ref = obj.get("ParentHotSpot")
        base = hot.get(ref, 0.0) if ref else 0.0
        if ref and ref not in hot:
            avisos.append("Un apoyo o carga referencia un punto no encontrado; se toma desde x = 0.")
        return base + (_v(obj, "x", 0.0) or 0.0)

    apoyos = []
    sup = comp.find("Supports")
    if sup is not None:
        for s in sup.findall("Object"):
            apoyos.append(Apoyo(
                x=x_abs(s), fijo_axial=s.get("SupportType") == "1",
                F_inv=abs(_v(s.find("SupportForce"), "Fsize", 0.0) or 0.0),
                rot_inv=abs(_v(s.find("Rotation"), "RotSize", 0.0) or 0.0),
                cy=abs(_v(s.find("Yielding"), "Yxy", 0.0) or 0.0), cz=abs(_v(s.find("Yielding"), "Yxz", 0.0) or 0.0)))
    apoyos.sort(key=lambda a: a.x)

    cargas = []
    lds = comp.find("Loads")
    if lds is not None:
        for l in lds.findall("Object"):
            rf, cl, mo = l.find("RadialForce"), l.find("ContinuousLoad"), l.find("Moment")
            c = Carga(x=x_abs(l), tipo_inv=l.get("Type", ""))
            c.Fy = _v(rf, "Fy", 0.0) or 0.0
            c.Fz = _v(rf, "Fz", 0.0) or 0.0
            c.Fx = _v(rf, "Fx", 0.0) or 0.0
            c.qy = _v(cl, "Qy", 0.0) or 0.0
            c.qz = _v(cl, "Qz", 0.0) or 0.0
            c.Lq = _v(cl, "Length", 0.0) or 0.0
            c.My = _v(mo, "Moy", 0.0) or 0.0
            c.Mz = _v(mo, "Moz", 0.0) or 0.0
            c.T = _v(mo, "Mkx", 0.0) or 0.0
            if any(abs(v) > 1e-9 for v in (c.Fy, c.Fz, c.Fx, c.qy, c.qz, c.My, c.Mz, c.T)):
                cargas.append(c)
            pr = _v(l, "Pressure", 0.0) or 0.0
            if abs(pr) > 1e-9:
                avisos.append("Hay una carga de presión en el modelo; no se considera en este cálculo.")
    cargas.sort(key=lambda c: c.x)

    mat = Material(
        nombre=comp.get("MatName", "Material"),
        E=_v(comp, "E", 206000.0), G=_v(comp, "G", 80000.0), nu=_v(comp, "mi", 0.3),
        Sy=_v(comp, "Sy", 0.0), Su=_v(comp, "Su", 0.0), rho=_v(comp, "Ro", 7860.0))

    inv = ResultadosInventor(
        masa=_v(sh, "Mass", 0.0), sigma_max=_v(sh, "SigmaMax", 0.0), tau_max=_v(sh, "ShearMax", 0.0),
        tors_max=_v(sh, "TorsionMax", 0.0), tens_max=_v(sh, "TensionMax", 0.0),
        red_max=_v(sh, "ReducedStressMax", 0.0), flecha_max=_v(sh, "MaxDefl", 0.0),
        giro_tors=_v(sh, "Atw", 0.0))

    return Eje(nombre=nombre, tramos=tramos, huecos=huecos, operaciones=ops, apoyos=apoyos,
               cargas=cargas, material=mat, usa_peso=sh.get("UseDensity") == "-1", inv=inv, avisos=avisos,
               beta=_v(sh, "Beta", 0.0) or 0.0, usa_beta=sh.get("UseBeta") == "-1")
