"""PASO 3 - Recalculo y verificacion de la transmision.

recalcular()     geometria, cinematica, fuerzas, potencia: formulas propias comparadas con el
                 Design Accelerator (desviacion %; tolerancia TOL_PCT).
comprobaciones() criterios de aceptacion con los limites (Min/Max) del propio XML.
"""
import math

TOL_PCT = 0.5   # desviacion aceptada entre el recalculo y el Design Accelerator


def v(d, k):
    return d["parametros"][k]["valor"] if "parametros" in d else d[k]["valor"]


def recalcular(datos):
    p1, p2 = datos["poleas"][0], datos["poleas"][1]
    c, cal = datos["correa"], datos["calculo"]
    nb = datos["transmision"]["nb"]["valor"]
    Dw1, Dw2 = v(p1, "Dw"), v(p2, "Dw")          # mm, diámetro primitivo
    Dp1 = v(p1, "Dp")                              # mm, diámetro efectivo
    C = v(p2, "C")                                 # mm
    n1, P1 = v(p1, "Speed"), v(p1, "P")            # rpm, kW
    q = v(c, "SpcMass")                            # kg/m
    w1 = n1 * 2 * math.pi / 60                     # rad/s

    r = {}

    def item(clave, simbolo, formula, valor, unidad, ref=None):
        dev = None if ref in (None, 0) else 100 * (valor - ref) / ref
        r[clave] = {"simbolo": simbolo, "formula": formula, "valor": valor,
                    "unidad": unidad, "da": ref, "desv_pct": dev}

    Dp2 = v(p2, "Dp")
    item("iD", "i_D", r"\frac{D_{p2}}{D_{p1}}", Dp2 / Dp1, "", v(p2, "iD"))
    item("i", "i", r"\frac{i_D}{1-s}", (Dp2 / Dp1) / (1 - v(cal, "s")), "", v(p2, "i"))
    L = 2 * C + math.pi * (Dw1 + Dw2) / 2 + (Dw2 - Dw1) ** 2 / (4 * C)
    item("Lw", "L_w", r"2C+\frac{\pi(D_{w1}+D_{w2})}{2}+\frac{(D_{w2}-D_{w1})^2}{4C}",
         L, "mm", v(c, "Lw"))
    b1 = math.degrees(math.pi - 2 * math.asin((Dw2 - Dw1) / (2 * C)))
    item("beta1", r"\beta_1", r"180^\circ-2\arcsin\frac{D_{w2}-D_{w1}}{2C}", b1, "deg", v(p1, "Beta"))
    vel = w1 * Dp1 / 2000
    item("v", "v", r"\omega_1\,\frac{D_{p1}}{2}", vel, "m/s", v(cal, "v"))
    T1 = P1 * 1000 / w1
    item("T1", "T_1", r"\frac{P_1}{\omega_1}", T1, "N·m", v(p1, "T"))
    Fp = 2000 * T1 / Dp1
    item("Fp", "F_p", r"\frac{2T_1}{D_{p1}}", Fp, "N", v(cal, "Fp"))
    Fc = nb * q * vel ** 2
    item("Fc", "F_c", r"n_b\,q\,v^2", Fc, "N", v(cal, "Fc"))
    F1, F2 = v(p1, "F1"), v(p1, "F2")
    item("Fe", "F_e", r"F_1-F_2", F1 - F2, "N", v(cal, "Fp"))
    item("Ft", "F_t", r"\frac{F_1+F_2}{2\,n_b}", (F1 + F2) / (2 * nb), "N", v(cal, "Ft"))
    item("FtMax", r"F_{t,max}", r"\frac{F_1}{n_b}", F1 / nb, "N", v(cal, "FtMax"))
    br = math.radians(v(p1, "Beta"))
    Fr = math.sqrt(F1 ** 2 + F2 ** 2 - 2 * F1 * F2 * math.cos(br))
    item("Fr", "F_r", r"\sqrt{F_1^2+F_2^2-2F_1F_2\cos\beta_1}", Fr, "N", v(p1, "Fr"))
    item("Fv", "F_v", r"(F_1+F_2)\sin\frac{\beta_1}{2}", (F1 + F2) * math.sin(br / 2), "N", v(p1, "Fv"))
    prb, c1, c3, c4, c5, c2 = (v(c, "PRB"), v(cal, "C1"), v(c, "C3"),
                               v(cal, "C4"), v(cal, "C5"), v(cal, "C2"))
    Pc = prb * c1 * c3 * c4 * c5
    item("Pcorrea", "P_R", r"P_{RB}\,C_1\,C_3\,C_4\,C_5", Pc, "kW")
    item("zer", "z_{req}", r"\frac{P_1\,C_2}{P_R}", P1 * c2 / Pc, "", v(cal, "zer"))
    item("Cpr", "C_{pr}", r"\frac{n_b\,P_R}{P_1}", nb * Pc / P1, "", v(cal, "Cpr"))
    item("eff", r"\eta", r"\frac{P_2}{P_1}", v(p2, "P") / P1, "", v(cal, "eff"))
    return r


def comprobaciones(datos, beta_min=120.0):
    cal, c = datos["calculo"], datos["correa"]
    nb = datos["transmision"]["nb"]["valor"]
    p1 = datos["poleas"][0]
    chk = []

    def add(desc, simb, val, op, lim, unidad=""):
        ok = val >= lim if op == ">=" else val <= lim
        chk.append({"descripcion": desc, "simbolo": simb, "valor": val, "operador": op,
                    "limite": lim, "unidad": unidad, "cumple": ok})

    add("Factor de seguridad de potencia", "C_{pr}", cal["Cpr"]["valor"], ">=", cal["Cpr"]["min"])
    add("Número de correas", "n_b", nb, ">=", cal["zer"]["valor"])
    add("Velocidad de la correa", "v", cal["v"]["valor"], "<=", cal["v"]["max"], "m/s")
    add("Frecuencia de flexión", "f_b", cal["fb"]["valor"], "<=", cal["fb"]["max"], "Hz")
    add("Tensión máxima por correa", r"F_{t,max}", cal["FtMax"]["valor"], "<=", cal["FtMax"]["max"], "N")
    for p in datos["poleas"]:
        add(f"Diámetro primitivo polea {p['posicion']}", rf"D_{{w{p['posicion']}}}",
            p["parametros"]["Dw"]["valor"], ">=", c["parametros"]["Dwmin"]["valor"], "mm")
    add("Ángulo de contacto polea menor", r"\beta_1", p1["parametros"]["Beta"]["valor"], ">=", beta_min, "deg")
    return chk


def verificar(datos, beta_min=120.0):
    rec, chk = recalcular(datos), comprobaciones(datos, beta_min)
    difs = [k for k, x in rec.items() if x["desv_pct"] is not None and abs(x["desv_pct"]) > TOL_PCT]
    return {"recalculo": rec, "comprobaciones": chk, "cumple": all(x["cumple"] for x in chk),
            "discrepancias_con_DA": difs}
