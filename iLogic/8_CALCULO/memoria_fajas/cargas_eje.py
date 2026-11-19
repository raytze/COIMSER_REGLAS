"""PASO 4 - Cargas que cada polea transmite a su eje (para la memoria del eje).

Por polea: par torsor, fuerza radial Fr y sus componentes en el plano de la transmision
(coordenadas X-Y del Design Accelerator):
    Fv    sobre la linea de centros, hacia la otra polea = (F1+F2)*sin(beta/2)
    Fperp perpendicular a la linea de centros            = |(F1-F2)*cos(beta/2)|
Fr actua en el plano medio de la polea; el signo de Fperp depende del sentido de giro.
"""
import math


def calcular(datos):
    poleas = datos["poleas"]
    cargas = []
    for k, p in enumerate(poleas):
        o = poleas[1 - k] if len(poleas) == 2 else poleas[(k + 1) % len(poleas)]
        g = lambda pp, s: pp["parametros"][s]["valor"]
        dx, dy = g(o, "X") - g(p, "X"), g(o, "Y") - g(p, "Y")
        ang_c = math.degrees(math.atan2(dy, dx))                 # hacia la otra polea
        F1, F2, beta = g(p, "F1"), g(p, "F2"), math.radians(g(p, "Beta"))
        Fv = (F1 + F2) * math.sin(beta / 2)
        Fperp = abs((F1 - F2) * math.cos(beta / 2))
        Fr = math.hypot(Fv, Fperp)
        cargas.append({
            "polea": p["posicion"], "designacion": p["designacion"],
            "motriz": p["motriz"],
            "centro_mm": [g(p, "X"), g(p, "Y")],
            "T_Nm": g(p, "T"), "n_rpm": g(p, "Speed"), "P_kW": g(p, "P"),
            "Fr_N": Fr, "Fv_N": Fv, "Fperp_N": Fperp,
            "angulo_linea_centros_deg": ang_c,
            "desvio_Fr_deg": math.degrees(math.atan2(Fperp, Fv)),
            "Fr_DA_N": g(p, "Fr"),
            "nota": "Fr actúa en el plano medio de la polea; signo de Fperp según sentido de giro",
        })
    return cargas
