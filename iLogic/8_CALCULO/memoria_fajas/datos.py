"""Datos de diseño que el generador de correas no guarda (proyecto, secciones de la memoria)."""
import configparser
import os

SECCIONES = ["datos", "correa", "geometria", "cinematica", "potencia",
             "fuerzas", "verificacion", "cargas_eje"]

PLANTILLA = """; ==========================================================
; DATOS DE LA MEMORIA DE LA TRANSMISIÓN POR CORREAS
; (todo lo técnico se lee del generador de correas trapezoidales de Inventor)
; Edite los valores y vuelva a ejecutar MEMORIA_FAJA.
; Las líneas que empiezan con ; son comentarios.
; ==========================================================

[proyecto]
empresa = COIMSER
proyecto = Proyecto
cliente = Cliente
codigo_documento = MC-FAJ-001
revision = 0
elaborado =
revisado =
aprobado =
designacion = {nombre}
; ruta de la imagen del logo (png/jpg/pdf). Vacío = logo de las reglas
logo =

[memoria]
; secciones a incluir, separadas por coma (o "todas"):
;   datos, correa, geometria, cinematica, potencia, fuerzas, verificacion, cargas_eje
secciones = todas

[verificacion]
; ángulo de contacto mínimo en la polea menor (grados)
angulo_contacto_min = 120
"""


def plantilla(nombre="Transmision"):
    return PLANTILLA.format(nombre=nombre)


class Datos:
    def __init__(self, ruta=None, nombre="Transmision"):
        cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";",))
        cp.read_string(plantilla(nombre))
        if ruta and os.path.exists(ruta):
            with open(ruta, encoding="utf-8-sig") as f:
                cp.read_file(f)
        self.cp = cp
        self.ruta = ruta
        self.avisos = []
        self.por_defecto = False

    def s(self, sec, k):
        return self.cp.get(sec, k, fallback="").strip()

    def f(self, sec, k, defecto=0.0):
        try:
            return float(self.s(sec, k).replace(",", "."))
        except ValueError:
            self.avisos.append(f"[{sec}] {k} = «{self.s(sec, k)}» no es un número; se usó {defecto}.")
            return defecto

    def secciones(self):
        t = self.s("memoria", "secciones").lower().replace(" ", "")
        if t in ("", "todas", "todo"):
            return list(SECCIONES)
        pedidas = [x for x in t.split(",") if x]
        malas = [x for x in pedidas if x not in SECCIONES]
        if malas:
            self.avisos.append(f"[memoria] secciones desconocidas: {', '.join(malas)}. Válidas: {', '.join(SECCIONES)}")
        return [x for x in SECCIONES if x in pedidas] or list(SECCIONES)
