"""Memoria de cálculo de transmisiones por correas trapezoidales (Design Accelerator de Inventor).

Pasos (cada uno se puede ejecutar solo; lee y escribe archivos en la carpeta CALCULOS):
  1 leer        Inventor -> <faja>.xml                (lo hace la regla MEMORIA_FAJA, o este
                                                       programa si se llama sin --xml)
  2 datos       <faja>.xml -> <faja>_datos.json       (unidades: mm, rpm, kW, N, N·m)
  3 verificar   -> <faja>_verificacion.json            (recálculo vs Inventor + criterios)
  4 cargas_eje  -> <faja>_cargas_eje.json              (Fr y T de cada polea, para el eje)
  5 memoria     -> Memoria_<faja>.tex / .pdf           (secciones según datos_<faja>.ini)

Uso:
  python main.py                              -> transmisión seleccionada (o la primera) en Inventor
  python main.py --xml faja.xml               -> sin Inventor
  python main.py --xml faja.xml --pasos 2 4   -> solo las cargas para el eje
  python main.py --xml faja.xml --pasos 5 --secciones verificacion cargas_eje
  opciones: --datos archivo.ini  --salida carpeta  --sin-pdf  --indice N  --abrir
"""
import argparse
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import cargas_eje  # noqa: E402
import datos  # noqa: E402
import memoria  # noqa: E402
import modelo  # noqa: E402
import verificar  # noqa: E402


def fajas_en_inventor():
    """PASO 1 sin iLogic: [(nombre, xml, ruta_ensamblaje)] de las transmisiones del documento activo."""
    import win32com.client as w
    app = w.GetActiveObject("Inventor.Application")
    doc = app.ActiveDocument
    if doc is None or doc.DocumentType != 12291:
        raise RuntimeError("Abra en Inventor el ensamblaje que contiene la transmisión por correas.")
    asm = w.CastTo(doc, "AssemblyDocument")
    encontrados = []

    def xml_de(oc):
        try:
            return oc.AttributeSets.Item("FDesign").Item("Data").Value
        except Exception:
            return None

    try:
        sel = asm.SelectSet
        for i in range(1, sel.Count + 1):
            x = xml_de(sel.Item(i))
            if x and "CAVBelts" in x[:400]:
                encontrados.append((sel.Item(i).Name, x, asm.FullFileName))
    except Exception:
        pass
    if encontrados:
        return encontrados

    def recorrer(occs):
        for i in range(1, occs.Count + 1):
            oc = occs.Item(i)
            x = xml_de(oc)
            if x and "CAVBelts" in x[:400]:
                encontrados.append((oc.Name, x, asm.FullFileName))
            try:
                if oc.SubOccurrences.Count:
                    recorrer(oc.SubOccurrences)
            except Exception:
                pass
    recorrer(asm.ComponentDefinition.Occurrences)
    if not encontrados:
        raise RuntimeError("No se encontró ninguna transmisión por correa trapezoidal en el ensamblaje activo.")
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
    carpeta, nombre = os.path.dirname(tex), os.path.basename(tex)
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
    for ext in (".pdf", ".tex"):
        ruta = base + ext
        if os.path.exists(ruta):
            dst = os.path.join(os.path.dirname(tex), "_SUPERADOS")
            os.makedirs(dst, exist_ok=True)
            shutil.move(ruta, os.path.join(dst, f"{os.path.basename(base)}_{sello}{ext}"))


def limpiar(nombre):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in nombre).strip("_") or "Faja"


def _json(ruta, obj=None):
    if obj is None:
        if not os.path.exists(ruta):
            return None
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return obj


def main():
    ap = argparse.ArgumentParser(description="Memoria de cálculo de transmisiones por correas trapezoidales")
    ap.add_argument("--xml")
    ap.add_argument("--datos")
    ap.add_argument("--salida")
    ap.add_argument("--pasos", nargs="*", type=int, default=[2, 3, 4, 5],
                    help="pasos a ejecutar: 2 datos, 3 verificar, 4 cargas_eje, 5 memoria")
    ap.add_argument("--secciones", nargs="*", choices=datos.SECCIONES,
                    help="secciones de la memoria (por defecto las del .ini)")
    ap.add_argument("--indice", type=int, default=1, help="transmisión a calcular si hay varias (1, 2, ...)")
    ap.add_argument("--sin-pdf", action="store_true")
    ap.add_argument("--abrir", action="store_true", help="abrir el PDF al terminar")
    ap.add_argument("--logo", help="logo por defecto si el archivo de datos no indica uno")
    ap.add_argument("--log", help="escribir la salida en este archivo (para iLogic)")
    ap.add_argument("--silencioso", action="store_true", help="sin ventanas: crea los datos por defecto y sigue")
    a = ap.parse_args()
    if a.log:
        f = open(a.log, "w", encoding="utf-8")
        sys.stdout = sys.stderr = f

    # ---------- PASO 1: XML ----------
    if a.xml:
        with open(a.xml, "rb") as f:
            xml = f.read()
        nombre = os.path.splitext(os.path.basename(a.xml))[0]
        base = os.path.dirname(os.path.abspath(a.xml))
        if not a.salida:
            a.salida = base
    else:
        fajas = fajas_en_inventor()
        if len(fajas) > 1:
            print("Transmisiones encontradas:", ", ".join(f"{i}) {e[0]}" for i, e in enumerate(fajas, 1)))
        nombre, xml_txt, ruta_asm = fajas[min(a.indice, len(fajas)) - 1]
        nombre = nombre.split(":")[0]
        base = os.path.join(os.path.dirname(ruta_asm), "CALCULOS")
        os.makedirs(base, exist_ok=True)
        ruta_xml = os.path.join(base, limpiar(nombre) + ".xml")
        with open(ruta_xml, "w", encoding="utf-16") as f:
            f.write(xml_txt)
        xml = xml_txt
        print("[1] XML:", ruta_xml)

    salida = a.salida or base
    os.makedirs(salida, exist_ok=True)
    nl = limpiar(nombre)
    r_datos = os.path.join(salida, f"{nl}_datos.json")
    r_ver = os.path.join(salida, f"{nl}_verificacion.json")
    r_car = os.path.join(salida, f"{nl}_cargas_eje.json")

    ini = a.datos or os.path.join(salida, f"datos_{nl}.ini")
    creado_ahora = False
    if 5 in a.pasos and not os.path.exists(ini):
        with open(ini, "w", encoding="utf-8") as f:
            f.write(datos.plantilla(nombre))
        print(f"Se creó el archivo de datos de la memoria: {ini}")
        if not a.silencioso:
            print("Complete proyecto, cliente, código y firmas y vuelva a ejecutar.")
            if os.name == "nt":
                os.startfile(ini)
            return 2
        print("Modo silencioso: se usan los valores por defecto.")
        creado_ahora = True
    dat = datos.Datos(ini, nombre)
    dat.por_defecto = creado_ahora
    if a.logo and not dat.s("proyecto", "logo") and os.path.exists(a.logo):
        dat.cp.set("proyecto", "logo", a.logo)

    # ---------- PASO 2: datos ----------
    if 2 in a.pasos:
        D = _json(r_datos, modelo.leer_xml(xml, nombre))
        print("[2] Datos:", r_datos)
    else:
        D = _json(r_datos) or modelo.leer_xml(xml, nombre)

    # ---------- PASO 3: verificación ----------
    beta_min = dat.f("verificacion", "angulo_contacto_min", 120.0)
    if 3 in a.pasos:
        V = _json(r_ver, verificar.verificar(D, beta_min))
        print("[3] Verificación:", r_ver)
        print("Resultado:", "OK" if V["cumple"] else "REVISAR")
        for c in V["comprobaciones"]:
            print(f"  [{'OK' if c['cumple'] else 'REVISAR'}] {c['descripcion']}: "
                  f"{c['valor']:.2f} {c['operador']} {c['limite']:.2f} {c['unidad']}")
        if V["discrepancias_con_DA"]:
            print("AVISO: el recálculo no coincide con Inventor en", ", ".join(V["discrepancias_con_DA"]),
                  "(¿falta pulsar Calcular en el generador de correas?).")
    else:
        V = _json(r_ver) or verificar.verificar(D, beta_min)

    # ---------- PASO 4: cargas sobre los ejes ----------
    if 4 in a.pasos:
        C = _json(r_car, cargas_eje.calcular(D))
        print("[4] Cargas sobre los ejes:", r_car)
        for c in C:
            print(f"  Polea {c['polea']} ({c['designacion']}{', motriz' if c['motriz'] else ''}): "
                  f"T = {c['T_Nm']:.2f} N·m, Fr = {c['Fr_N']:.1f} N")
    else:
        C = _json(r_car) or cargas_eje.calcular(D)

    # ---------- PASO 5: memoria ----------
    if 5 in a.pasos:
        tex = os.path.join(salida, f"Memoria_{nl}.tex")
        superar(tex)
        memoria.generar(D, V, C, dat, tex, a.secciones)
        print("[5] Memoria LaTeX:", tex)
        for av in dat.avisos:
            print("AVISO:", av)
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
