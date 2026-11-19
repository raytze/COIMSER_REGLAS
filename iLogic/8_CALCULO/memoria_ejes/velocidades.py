# -*- coding: utf-8 -*-
"""Velocidades criticas (resonancia) del eje: flexion lateral (autovalores del modelo FE) y torsion (2 inercias)."""
import math

from calculo import _resolver_banda

MAX_MODOS = 3


def _modos(c, plano):
    """Primeras frecuencias naturales laterales (rad/s) en el plano 'y' o 'z'. Masa concentrada en los nodos."""
    Kc = c._Kplanos[plano]
    n = len(c.x)
    nd = 2 * n
    m = [0.0] * nd
    if c.vel["incluir_eje"]:
        for el in c.elem:
            ma = c.rho * el["A"] * (el["b"] - el["a"]) * 1e-9  # kg
            i = c._idx(el["a"])
            j = c._idx(el["b"])
            m[2 * i] += ma / 2
            m[2 * j] += ma / 2
    for mm in c.vel["masas"]:
        m[2 * c._idx(mm["x"])] += mm["kg"]
    for d in c._rigidos[plano]:
        m[d] = 0.0
    if sum(m) <= 0:
        return []
    modos, phis = [], []
    for k in range(MAX_MODOS):
        x = [math.sin((k + 1) * math.pi * (i // 2) / max(n - 1, 1)) + 0.1 * ((i * 7919) % 13) / 13 if i % 2 == 0 else 0.0
             for i in range(nd)]
        lam_ant = None
        lam = 0.0
        for _ in range(80):
            rhs = [m[i] * x[i] for i in range(nd)]
            x = _resolver_banda(Kc, rhs, 3)
            for ph in phis:
                s = sum(ph[i] * m[i] * x[i] for i in range(nd))
                x = [x[i] - s * ph[i] for i in range(nd)]
            nm = math.sqrt(sum(m[i] * x[i] ** 2 for i in range(nd)))
            if nm <= 0:
                break
            x = [v / nm for v in x]
            num = sum(x[i] * sum(Kc[i][j] * x[j] for j in range(max(0, i - 3), min(nd, i + 4))) for i in range(nd))
            lam = num  # x^T M x = 1
            if lam_ant is not None and abs(lam - lam_ant) <= 1e-10 * abs(lam):
                break
            lam_ant = lam
        if lam <= 0:
            break
        phis.append(x)
        modos.append(math.sqrt(lam * 1000.0))  # N/mm/kg -> 1/s^2 : x1000
    return modos


def calcular(c):
    v = c.vel
    res = dict(modos={}, tors=None, masas=v["masas"], rpm=v["rpm"], margen=v["margen"], incluir_eje=v["incluir_eje"])
    for plano in ("y", "z"):
        res["modos"][plano] = [w * 60 / (2 * math.pi) for w in _modos(c, plano)]
    # torsion: dos inercias
    con_ip = [m for m in v["masas"] if m["Ip"] > 0]
    if len(con_ip) == 2:
        a, b = sorted(con_ip, key=lambda m: m["x"])
        flex = 0.0
        for el in c.elem:
            if el["a"] >= a["x"] - 1e-6 and el["b"] <= b["x"] + 1e-6:
                flex += (el["b"] - el["a"]) / (c.G * el["J"])  # rad/(N mm)
        if flex > 0:
            kt = 1.0 / flex * 1e-3  # N m / rad
            I1, I2 = a["Ip"], b["Ip"]
            w = math.sqrt(kt * (I1 + I2) / (I1 * I2))
            res["tors"] = dict(kt=kt, I1=I1, I2=I2, n=w * 60 / (2 * math.pi), x1=a["x"], x2=b["x"])
    return res


def _sep(rpm, ns, margen):
    """Peor separacion relativa |n - nc| / nc entre la velocidad de giro y las criticas (en %)."""
    peor, nc_p = None, None
    for nc in ns:
        s = abs(rpm - nc) / nc * 100
        if peor is None or s < peor:
            peor, nc_p = s, nc
    return peor, nc_p
