"""Memoria de cálculo de ejes desde el Shaft Generator de Inventor.

Uso:
  python main.py                 -> toma el eje seleccionado (o el primero) del ensamblaje activo en Inventor
  python main.py --xml eje.xml   -> trabaja con un XML exportado (sin Inventor)
  opciones: --datos archivo.ini  --salida carpeta  --sin-pdf  --indice N
"""
import argparse
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import calculo  # noqa: E402
import datos  # noqa: E402
import memoria  # noqa: E402
import modelo  # noqa: E402


def ejes_en_inventor():
    """Devuelve [(nombre, xml, ruta_ensamblaje)] de los ejes del Shaft Generator del documento activo."""
    import win32com.client as w
    app = w.GetActiveObject("Inventor.Application")
    doc = app.ActiveDocument
    if doc is None or doc.DocumentType != 12291:
        raise RuntimeError("Abra en Inventor el ensamblaje que contiene el eje del generador de ejes.")
    asm = w.CastTo(doc, "AssemblyDocument")
    encontrados = []

    def xml_de(oc):
        try:
            return oc.AttributeSets.Item("FDesign").Item("Data").Value
        except Exception:
            return None

    # 1) si hay un componente seleccionado, ese primero
    try:
        sel = asm.SelectSet
        for i in range(1, sel.Count + 1):
            x = xml_de(sel.Item(i))
            if x and "CAShaft" in x[:400]:
                encontrados.append((sel.Item(i).Name, x, asm.FullFileName))
    except Exception:
        pass
    if encontrados:
        return encontrados

    def recorrer(occs):
        for i in range(1, occs.Count + 1):
            oc = occs.Item(i)
            x = xml_de(oc)
            if x and "CAShaft" in x[:400]:
                encontrados.append((oc.Name, x, oc.Parent.Document.FullFileName if hasattr(oc.Parent, "Document") else asm.FullFileName))
            try:
                if oc.SubOccurrences.Count:
                    recorrer(oc.SubOccurrences)
            except Exception:
                pass
    recorrer(asm.ComponentDefinition.Occurrences)
    if not encontrados:
        raise RuntimeError("No se encontró ningún eje del generador de ejes en el ensamblaje activo.")
    return encontrados


def _pdflatex():
    import shutil
    exe = shutil.which("pdflatex")
    if exe:
        return exe
    cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "MiKTeX", "miktex", "bin", "x64", "pdflatex.exe")
    if os.path.exists(cand):
        return cand
    raise RuntimeError("No se encontró pdflatex (MiKTeX). Se generó solo el archivo .tex.")


def compilar(tex):
    carpeta = os.path.dirname(tex)
    nombre = os.path.basename(tex)
    exe = _pdflatex()
    for _ in range(2):  # dos pasadas: índice y número de páginas
        r = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", nombre],
                           cwd=carpeta, capture_output=True, text=True, errors="replace",
                           stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            log = os.path.splitext(tex)[0] + ".log"
            raise RuntimeError(f"Error al compilar LaTeX. Revise {log}\n" + r.stdout[-2500:])
    for ext in (".aux", ".out", ".toc", ".log"):
        try:
            os.remove(os.path.splitext(tex)[0] + ext)
        except OSError:
            pass
    return os.path.splitext(tex)[0] + ".pdf"


def superar(tex):
    """La memoria anterior no se sobrescribe: se mueve a _SUPERADOS con fecha y hora."""
    import datetime
    import shutil
    base = os.path.splitext(tex)[0]
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pares = [(base + ext, os.path.basename(base)) for ext in (".pdf", ".tex")]
    ver = os.path.join(os.path.dirname(tex), "Verificacion_" + os.path.basename(base).replace("Memoria_", "", 1))
    pares.append((ver + ".xlsx", os.path.basename(ver)))
    for ruta, nom in pares:
        if os.path.exists(ruta):
            dst = os.path.join(os.path.dirname(tex), "_SUPERADOS")
            os.makedirs(dst, exist_ok=True)
            shutil.move(ruta, os.path.join(dst, f"{nom}_{sello}{os.path.splitext(ruta)[1]}"))


def limpiar(nombre):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in nombre).strip("_") or "Eje"


def main():
    ap = argparse.ArgumentParser(description="Memoria de cálculo de ejes (Shaft Generator de Inventor)")
    ap.add_argument("--xml")
    ap.add_argument("--datos")
    ap.add_argument("--salida")
    ap.add_argument("--indice", type=int, default=1, help="eje a calcular si hay varios (1, 2, ...)")
    ap.add_argument("--sin-pdf", action="store_true")
    ap.add_argument("--abrir", action="store_true", help="abrir el PDF al terminar")
    ap.add_argument("--logo", help="logo por defecto si el archivo de datos no indica uno")
    ap.add_argument("--log", help="escribir la salida en este archivo (para iLogic)")
    ap.add_argument("--silencioso", action="store_true", help="sin ventanas: crea los datos por defecto y sigue")
    a = ap.parse_args()
    if a.log:
        f = open(a.log, "w", encoding="utf-8")
        sys.stdout = sys.stderr = f

    if a.xml:
        with open(a.xml, "rb") as f:
            xml = f.read()
        nombre = os.path.splitext(os.path.basename(a.xml))[0]
        base = os.path.dirname(os.path.abspath(a.xml))
        if not a.salida:
            a.salida = base
    else:
        ejes = ejes_en_inventor()
        if len(ejes) > 1:
            print("Ejes encontrados:", ", ".join(f"{i}) {e[0]}" for i, e in enumerate(ejes, 1)))
        nombre, xml, ruta_asm = ejes[min(a.indice, len(ejes)) - 1]
        nombre = nombre.split(":")[0]
        base = os.path.dirname(ruta_asm)

    salida = a.salida or os.path.join(base, "CALCULOS")
    os.makedirs(salida, exist_ok=True)
    ini = a.datos or os.path.join(salida, f"datos_{limpiar(nombre)}.ini")
    creado_ahora = False
    if not os.path.exists(ini):
        with open(ini, "w", encoding="utf-8") as f:
            f.write(datos.plantilla(nombre))
        print(f"Se creó el archivo de datos de diseño: {ini}")
        if not a.silencioso:
            print("Revise los valores (rpm, tipo de carga, confiabilidad, límites) y vuelva a ejecutar.")
            if os.name == "nt":
                os.startfile(ini)
            return 2
        print("Modo silencioso: se calcula con los valores por defecto.")
        creado_ahora = True

    eje = modelo.leer_xml(xml, nombre)
    dat = datos.Datos(ini, nombre)
    dat.por_defecto = creado_ahora
    if a.logo and not dat.s("proyecto", "logo") and os.path.exists(a.logo):
        dat.cp.set("proyecto", "logo", a.logo)
    c = calculo.Calculo(eje, dat)
    import math
    difs = [abs(math.hypot(ry, rz) / a.F_inv - 1) for a, ry, rz in zip(eje.apoyos, c.Ry, c.Rz) if a.F_inv > 1e-6]
    if not difs or max(difs) > 0.02:
        print("AVISO: los resultados del generador de ejes no coinciden con este cálculo "
              "(¿falta pulsar Calcular en el Shaft Generator?). La memoria usa el cálculo propio.")
    tex = os.path.join(salida, f"Memoria_{limpiar(nombre)}.tex")
    superar(tex)
    memoria.generar(c, tex)
    print("Memoria LaTeX:", tex)
    try:
        import excel
        xlsx = os.path.join(salida, "Verificacion_" + limpiar(nombre) + ".xlsx")
        excel.generar(c, xlsx)
        print("Excel de verificación:", xlsx)
    except Exception as ex:  # el Excel es un anexo: si falla no se pierde la memoria
        print("AVISO: no se pudo generar el Excel de verificación:", ex)
    print("Resultado:", "OK" if c.todo_ok else "REVISAR")
    for cr in c.criterios:
        print(f"  [{'OK' if cr['ok'] else 'REVISAR'}] {cr['nombre']}: {cr['valor']} ({cr['lim']}) en {cr['sec']}")
    if not a.sin_pdf:
        pdf = compilar(tex)
        print("PDF:", pdf)
        if a.abrir and os.name == "nt":
            os.startfile(pdf)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as ex:  # mensaje claro para el usuario de iLogic
        print("ERROR:", ex)
        sys.stdout.flush()
        sys.exit(1)
