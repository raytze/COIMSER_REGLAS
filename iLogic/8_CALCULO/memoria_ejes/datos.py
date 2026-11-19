"""Datos de diseño que Inventor no guarda, y tablas de los documentos fuente.

Tablas transcritas del documento «Cálculo de ejes de poleas — método completo»
(secciones 9.1 a 9.9), que a su vez cita: PDF «CAP 7-A Cálculo de ejes de
transmisión y de máquinas» (ASME, rigidez, Soderberg) y Bavaresco,
«Procedimiento para el diseño de ejes» (Von Mises / ANSI B106.1M).
"""
import configparser
import os

KSI_A_MPA = 6.894757

# 9.1 Factores ASME Cm / Ct (en los rangos se toma el valor mayor)
CARGAS_ASME = {
    "1": ("Eje estacionario, carga aplicada gradualmente", 1.0, 1.0),
    "2": ("Eje estacionario, carga aplicada súbitamente", 2.0, 2.0),
    "3": ("Eje giratorio, carga constante o gradualmente aplicada", 1.5, 1.0),
    "4": ("Eje giratorio, carga súbita con choques menores", 2.0, 1.5),
    "5": ("Eje giratorio, carga súbita con choques mayores", 3.0, 3.0),
}

# 9.2 Límites de rigidez
FLECHA = {  # coeficiente en in por pie de longitud entre apoyos
    "transmision": ("Ejes de transmisión: 0.01 in/pie", 0.01),
    "maquina_0.002": ("Ejes de máquinas: 0.002 in/pie", 0.002),
    "maquina_0.001": ("Ejes de máquinas: 0.001 in/pie", 0.001),
}
TORSION = {  # (descripción, minutos por pie) ; None = 1° cada 20 diámetros
    "general": ("En general: 5.0 min/pie", 5.0),
    "ordinario": ("Máquinas, servicio ordinario: 6.0 min/pie", 6.0),
    "variable": ("Máquinas, cargas variables: 4.5 min/pie", 4.5),
    "reversible": ("Máquinas, cargas reversibles súbitas: 3.0 min/pie", 3.0),
    "20d": ("Ejes de transmisión: 1° por cada 20 diámetros", None),
}

# 9.4 Factor de apoyo n (Euler)
APOYO_EULER = {
    "rodamientos": ("Extremos articulados (rodamientos)", 1.00),
    "fijos": ("Extremos fijos (empotrados)", 2.25),
    "parcial": ("Extremos parcialmente restringidos (bocinas, cojinetes)", 1.60),
}

# 9.6 Confiabilidad: factor B ; Cr = 1 - 0.076·B
CONFIABILIDAD_B = {"50": 0.0, "67": 0.44, "84": 1.0, "90": 1.3, "95": 1.6, "99": 2.3, "99.99": 3.7}

# 9.7 Concentración de esfuerzos Kf (Bavaresco figs. 8 y 9)
KF_CHAVETERO = {"perfil": 1.6, "patin": 1.3, "ninguno": 1.0}
KF_HOMBRO_REDONDEADO = 1.5
KF_HOMBRO_CORTANTE = 2.5

# 9.9 Tabla Nº 1 de Bavaresco: (Su ksi, Sy ksi)
BAVARESCO = {
    "Hierro dulce Laminado simple": (48, 25), "C1010 Estirado en frio": (67, 55),
    "C1015 Estirado en frio": (77, 63), "C1020 Laminado simple": (65, 48),
    "C1020 Normalizado": (64, 50), "C1020 Recocido": (57, 42), "C1020 Estirado en frio": (78, 66),
    "C1022 Laminado simple": (72, 52), "C1030 Laminado simple": (80, 51),
    "C1035 Laminado simple": (85, 55), "C1045 Laminado simple": (96, 59),
    "C1095 Normalizado": (141, 80), "B1113 Acabado en frio": (83, 72), "B1113 Laminado simple": (70, 45),
    "C1118 Laminado simple": (75, 46), "C1118 Estirado en frio": (80, 75), "C1144 OQT 1000": (118, 83),
    "1340 OQT 1200": (113, 92), "1345 OQT 800": (187, 175), "2317 OQT 1000": (79, 71),
    "2340 OQT 1000": (137, 120), "3150 OQT 1000": (151, 130), "3250 OQT 1000": (166, 146),
    "4363 OQT 1000": (180, 160), "4130 WQT 1100": (127, 114), "4130 Estirado en frio": (122, 105),
    "4340 Estirado en frio": (122, 105), "4640 OQT 1000": (152, 130), "5140 OQT 1000": (150, 128),
    "5140 Estirado en frio": (105, 88), "8630 Estirado en frio": (115, 100), "8640 OQT 1000": (160, 150),
    "8760 OQT 800": (220, 200), "9255 OQT 1000": (180, 160), "9440 OQT 1000": (152, 135),
    "9850 OQT 1100": (180, 158),
}

# Co (esfuerzos residuales, Bavaresco): 1.3 laminado o estirado en frío; 1.0 normalizado,
# recocido; templado y revenido 1.0 (supuesto del documento)
CO_ESTADO = {"mecanizado": 1.0, "laminado": 1.3, "estirado": 1.3, "normalizado": 1.0, "recocido": 1.0, "templado": 1.0}


PLANTILLA = """; ==========================================================
; DATOS DE DISEÑO DEL EJE (lo que el Shaft Generator no guarda)
; Edite los valores y vuelva a ejecutar la memoria de cálculo.
; Las líneas que empiezan con ; son comentarios.
; ==========================================================

[proyecto]
empresa = COIMSER
proyecto = Proyecto
cliente = Cliente
codigo_documento = MC-EJE-001
revision = 0
elaborado =
revisado =
aprobado =
designacion_eje = {nombre}
; ruta de la imagen del logo (png/jpg/pdf). Vacío = recuadro para el logo
logo =

[operacion]
; velocidad de giro del eje (rpm)
rpm = 100
; tipo de carga ASME (tabla Cm/Ct):
;   1 estacionario gradual | 2 estacionario súbita | 3 giratorio gradual
;   4 giratorio con choques menores | 5 giratorio con choques mayores
tipo_carga_asme = 3
; si en Inventor solo hay un torsor, ese es la ENTRADA (motorreductor). Por dónde SALE:
;   auto (punto de mayor carga radial: polea, piñón...) | izquierda | derecha | o una x en mm
salida_torque = auto
; incluir el peso propio del eje: si | no | inventor (lo que diga el Shaft Generator)
peso_propio = inventor

[material]
; inventor = usa Sy y Su del Shaft Generator
; o el nombre de la Tabla Nº 1 de Bavaresco, por ejemplo: C1045 Laminado simple
fuente = inventor
; estado de la superficie/acero para el factor Co: mecanizado (por defecto, 1.0) | laminado | estirado (1.3, solo si la
; superficie queda tal como sale del laminado o estirado) | normalizado | recocido | templado
estado = mecanizado

[fatiga]
; factor de seguridad del eje (Von Mises, Bavaresco ec. 19)
N_von_mises = 2
; factor de seguridad mínimo por Soderberg (PDF 7-A)
N_min_soderberg = 1.2
; confiabilidad (%): 50 | 67 | 84 | 90 | 95 | 99 | 99.99
confiabilidad = 90
; Kf de hombros con empalme: auto (Peterson, segun r/d y D/d) | fijo (1.5 redondeado, 2.5 cortante)
kf_hombro = auto
; aplicar el factor de tamano Kb a Sn en Von Mises: si | no
tamano_en_von_mises = si
; temperatura del eje (°C)
temperatura = 25
; tipo de chavetero: perfil (Kf 1.6) | patin (Kf 1.3)
chavetero = perfil
; Kf de efectos diversos (corrosión, recubrimientos...)
kf_diversos = 1.0

[ranuras]
; Concentradores en el fondo de ranuras de anillo, desahogos y roscas.
; Kf en el fondo (los anillos suelen dar 3 a 5 segun la geometria; AJUSTAR con la fuente del anillo)
kf_ranura = 3.0
kf_desahogo = 2.5
kf_rosca = 2.5
; profundidad radial (mm) para calcular con el diametro del FONDO (d = D - 2 x profundidad).
; 0 = no se reduce el diametro (se usa el nominal; NO conservador si la ranura es profunda)
profundidad = 0

[asme]
; aplicar 75 % de Ssd también en hombros y ranuras (el PDF 7-A lo pide): si | no
reducir_en_hombros = si
; apoyo para compresión (Euler): rodamientos | fijos | parcial
apoyo_euler = rodamientos

[velocidades]
; Velocidades criticas (resonancia). Los engranes, poleas y acoplamientos NO tienen masa en el Shaft Generator:
; sin ellos el resultado es solo una COTA SUPERIOR. Declarar las masas montadas en el eje.
; rpm = velocidad de giro del eje. Vacio o 0 = se usa la rpm de [operacion] (una sola velocidad de giro)
; margen = separacion minima exigida entre la velocidad de giro y cada critica, en %
; incluir_eje = si | no   (masa propia del eje)
; masa_N = nombre | x [mm] | masa [kg] | Ip [kg*m2, opcional, para la critica torsional con 2 inercias]
rpm =
margen = 25
incluir_eje = si
masa_1 =
masa_2 =
masa_3 =
masa_4 =
masa_5 =
masa_6 =

[casos]
; Casos de carga adicionales: se verifica la FLUENCIA ESTATICA (Von Mises, Sy/sigma') en todas las
; secciones. El caso nominal es siempre el del generador de ejes (todas las verificaciones).
; Formato:  caso_N = nombre | factor torque | factor cargas radiales | factor axial | FS minimo
; Los factores multiplican los torsores, las cargas radiales/distribuidas/momentos y las axiales.
; Por defecto: arranque del motor con 2 veces el torque nominal y las fuerzas de los elementos
; transmisores (engranes, poleas, cadenas) proporcionales al torque. AJUSTAR segun el motor.
; Dejar el caso vacio para no usarlo. Se pueden definir hasta 4 casos.
caso_1 = Arranque del motor | 2.0 | 2.0 | 1.0 | 1.5
caso_2 =
caso_3 =
caso_4 =

[rigidez]
; flecha permisible: transmision (0.01 in/pie) | maquina_0.002 | maquina_0.001
flecha = transmision
; ángulo de torsión permisible: general | ordinario | variable | reversible | 20d
torsion = general
; pendiente máxima en los puntos de carga (tan alfa). CEMA fig. 8.11: 0.0023 ; 0.0015
tan_alfa_limite = 0.0023
"""


def plantilla(nombre="Eje"):
    return PLANTILLA.format(nombre=nombre)


class Datos:
    def __init__(self, ruta=None, nombre="Eje"):
        cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";",))
        cp.read_string(plantilla(nombre))
        if ruta and os.path.exists(ruta):
            with open(ruta, encoding="utf-8-sig") as f:
                cp.read_file(f)
        self.cp = cp
        self.ruta = ruta
        self.avisos = []
        self.por_defecto = False

    def _aviso(self, txt):
        if txt not in self.avisos:
            self.avisos.append(txt)

    def _clave(self, sec, k, tabla, defecto, nombre):
        """Busca la clave sin distinguir mayusculas ni espacios; si no existe avisa y usa el valor por defecto."""
        t = self.s(sec, k).strip().lower().replace(" ", "")
        for kk in tabla:
            if kk.lower().replace(" ", "") == t:
                return tabla[kk]
        if t:
            self._aviso(f"[{sec}] {k} = «{self.s(sec, k)}» no es válido; se usó «{defecto}» ({nombre}). Valores posibles: " + ", ".join(tabla))
        return tabla[defecto]

    def s(self, sec, k):
        return self.cp.get(sec, k, fallback="").strip()

    def f(self, sec, k):
        return float(self.s(sec, k).replace(",", "."))

    # ---- valores derivados ----
    def asme(self):
        return self._clave("operacion", "tipo_carga_asme", CARGAS_ASME, "3", "tipo de carga ASME")

    def cr(self):
        txt = self.s("fatiga", "confiabilidad").replace("%", "").strip()
        try:
            v = float(txt.replace(",", "."))
        except ValueError:
            self._aviso(f"[fatiga] confiabilidad = «{txt}» no es numérica; se usó 90 %.")
            v = 90.0
        # se usa la confiabilidad tabulada igual o inmediatamente MAYOR (conservador)
        tab = sorted(float(k) for k in CONFIABILIDAD_B)
        mayores = [t for t in tab if t >= v - 1e-9]
        usado = mayores[0] if mayores else tab[-1]
        if abs(usado - v) > 1e-9:
            self._aviso(f"[fatiga] confiabilidad = {v:g} % no está tabulada; se usó {usado:g} % (la tabulada igual o mayor).")
        B = CONFIABILIDAD_B[next(k for k in CONFIABILIDAD_B if abs(float(k) - usado) < 1e-9)]
        return B, 1 - 0.076 * B

    def cb(self):
        T = self.f("fatiga", "temperatura")
        return 1.0 if T < 100 else (0.8 if T <= 200 else 0.6)

    def co(self):
        e = self.s("material", "estado").lower()
        for k, v in CO_ESTADO.items():
            if e.startswith(k):
                if v > 1.0:
                    self._aviso(f"[material] estado = {k}: Co = {v:g} solo es válido si la superficie queda sin mecanizar. "
                                "Para piezas mecanizadas use estado = mecanizado.")
                return v
        if e:
            self._aviso(f"[material] estado = «{e}» no reconocido; se usó Co = 1.0. Valores: " + ", ".join(CO_ESTADO))
        return 1.0

    def kf_chavetero(self):
        t = self.s("fatiga", "chavetero").lower().replace("í", "i").replace("é", "e")
        if t not in KF_CHAVETERO and t:
            self._aviso(f"[fatiga] chavetero = «{t}» no es válido; se usó «perfil» (Kf = 1.6). Valores: perfil, patin, ninguno.")
        return KF_CHAVETERO.get(t, 1.6)

    def ranura(self, tipo):
        """(Kf, profundidad mm) para Ranura / Desahogo / Rosca."""
        k = {"Ranura": "kf_ranura", "Desahogo": "kf_desahogo", "Rosca": "kf_rosca"}.get(tipo, "kf_ranura")
        return self.f("ranuras", k), self.f("ranuras", "profundidad")

    def casos(self):
        """Casos de carga adicionales definidos en [casos]: lista de dict."""
        out = []
        for k in range(1, 5):
            txt = self.s("casos", f"caso_{k}")
            if not txt:
                continue
            p = [x.strip() for x in txt.split("|")]
            try:
                out.append(dict(nombre=p[0] or f"Caso {k}",
                                ft=float(p[1].replace(",", ".")) if len(p) > 1 and p[1] else 1.0,
                                fr=float(p[2].replace(",", ".")) if len(p) > 2 and p[2] else 1.0,
                                fa=float(p[3].replace(",", ".")) if len(p) > 3 and p[3] else 1.0,
                                fs=float(p[4].replace(",", ".")) if len(p) > 4 and p[4] else 1.5))
            except ValueError:
                raise ValueError(f"[casos] caso_{k}: formato incorrecto. Use: nombre | f.torque | f.radial | f.axial | FS minimo")
        return out

    def velocidades(self):
        """Parametros de [velocidades]: rpm, margen %, incluir_eje, masas puntuales."""
        def num(t, k):
            try:
                return float(str(t).replace(",", ".")) if str(t).strip() else 0.0
            except ValueError:
                raise ValueError(f"[velocidades] {k}: valor numerico incorrecto: {t!r}")
        masas = []
        for k in range(1, 7):
            txt = self.s("velocidades", f"masa_{k}")
            if not txt:
                continue
            p = [x.strip() for x in txt.split("|")]
            if len(p) < 3:
                raise ValueError("[velocidades] masa_%d: formato: nombre | x [mm] | masa [kg] | Ip [kg*m2]" % k)
            masas.append(dict(nombre=p[0] or f"Masa {k}", x=num(p[1], "x"), kg=num(p[2], "masa"),
                              Ip=num(p[3], "Ip") if len(p) > 3 else 0.0))
        rpm = num(self.s("velocidades", "rpm"), "rpm")
        if rpm <= 0:
            rpm = num(self.s("operacion", "rpm"), "rpm")  # una sola velocidad de giro: la de [operacion]
        return dict(rpm=rpm, margen=num(self.s("velocidades", "margen") or 25, "margen"),
                    incluir_eje=not self.s("velocidades", "incluir_eje").lower().startswith("n"), masas=masas)

    def flecha(self):
        return self._clave("rigidez", "flecha", FLECHA, "transmision", "flecha permisible")

    def torsion(self):
        return self._clave("rigidez", "torsion", TORSION, "general", "torsión permisible")

    def euler(self):
        return self._clave("asme", "apoyo_euler", APOYO_EULER, "rodamientos", "apoyo para Euler")

    def material_bavaresco(self):
        nom = self.s("material", "fuente")
        if nom.lower() == "inventor":
            return None
        clave = nom.lower().replace("í", "i")
        for k, v in BAVARESCO.items():
            if k.lower() == clave:
                return k, v[0] * KSI_A_MPA, v[1] * KSI_A_MPA
        raise ValueError(f"Material «{nom}» no está en la Tabla Nº 1 de Bavaresco.")
