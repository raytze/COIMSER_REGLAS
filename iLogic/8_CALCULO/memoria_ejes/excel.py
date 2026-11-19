"""Libro Excel de verificacion con formulas vivas (una hoja por tema) para la memoria del eje.

Las solicitaciones de cada seccion (My, Mz, T, N) salen del modelo de elementos finitos de la memoria y se
escriben como DATOS (azul sobre amarillo). Todo lo demas (esfuerzos, ASME, Von Mises, Soderberg, torsion,
casos de carga) son FORMULAS: si se cambia un diametro, un material o un factor, el libro recalcula.
Permite que otra persona compruebe a mano cada seccion critica sin usar el programa.
"""
import math
from xlsxmin import Libro, ref

EPS = 1e-7


def generar(c, ruta):
    e, d = c.eje, c.dat
    lib = Libro()
    hRes = lib.hoja("Resumen")
    hDat = lib.hoja("Datos")
    hSec = lib.hoja("Secciones")
    hTor = lib.hoja("Torsion")
    hCas = lib.hoja("Casos") if c.casos else None

    # ============================================================ DATOS
    hDat.set(1, 1, "Datos de entrada y factores", "titulo")
    hDat.set(2, 1, f"Eje: {e.nombre}.  Celdas azules sobre amarillo = datos (editables). Celdas negras = formulas.", "nota1")
    for j, t in enumerate(("Parámetro", "Valor", "Unidad", "Fuente / observación"), 1):
        hDat.set(4, j, t, "enc")
    desc_tors, minpie = d.torsion()
    items = [
        ("Sy", "Límite de fluencia Sy", c.Sy, "MPa", "in1", "Material (Shaft Generator o Tabla Nº 1 de Bavaresco)"),
        ("Su", "Resistencia a la tracción Su", c.Su, "MPa", "in1", "Material (Shaft Generator o Tabla Nº 1 de Bavaresco)"),
        ("E", "Módulo de elasticidad E", c.E, "MPa", "in0", "Shaft Generator"),
        ("G", "Módulo de rigidez G", c.G, "MPa", "in0", "Shaft Generator"),
        ("Cm", "Factor de carga Cm (flexión, ASME)", c.Cm, "-", "in2", f"ASME: {c.asme_desc}"),
        ("Ct", "Factor de carga Ct (torsión, ASME)", c.Ct, "-", "in2", f"ASME: {c.asme_desc}"),
        ("Cb", "Factor de temperatura Cb", c.Cb, "-", "in2", "Archivo de datos: temperatura"),
        ("Cs", "Factor de superficie Cs", c.Cs, "-", "in3", "Bavaresco, gráfico Nº 1 (curva «Mecanizado»), lectura lineal"),
        ("Cr", "Factor de confiabilidad Cr", c.Cr, "-", "in3", f"Confiabilidad {d.s('fatiga', 'confiabilidad')} %  (Cr = 1 - 0.076 B, B = {c.B:g})"),
        ("Co", "Factor de estado del acero Co", c.Co, "-", "in2", "Archivo de datos: estado del acero"),
        ("kfd", "Kf de efectos diversos", c.kf_div, "-", "in2", "Archivo de datos"),
        ("tvm", "Kb también en Von Mises (1 = sí, 0 = no)", 1 if c.tam_vm else 0, "-", "in0", "Archivo de datos: tamano_en_von_mises"),
        ("Nvm", "Factor de seguridad requerido (Von Mises)", c.N_vm, "-", "in2", "Archivo de datos"),
        ("Nsod", "Factor de seguridad mínimo (Soderberg)", c.N_sod, "-", "in2", "Archivo de datos"),
        ("minpie", "Torsión permisible", (minpie if minpie else 0.0), "min/pie", "in2",
         f"{desc_tors}. Si es 0 se usa 1° cada 20 diámetros"),
        ("tan", "Pendiente máxima en puntos de carga (tan α)", c.tan_lim, "-", "in4", "CEMA fig. 8.11"),
    ]
    A = {}
    fila = 5
    for k, lab, val, uni, est, nota in items:
        hDat.set(fila, 1, lab, "celda"); hDat.set(fila, 2, val, est); hDat.set(fila, 3, uni, "celda"); hDat.set(fila, 4, nota, "celda")
        A[k] = f"Datos!$B${fila}"
        fila += 1
    derivados = [
        ("Snp", "Límite de fatiga de la probeta Sn' = 0.5 Su", f"=0.5*{A['Su']}", "MPa", "f1", "Bavaresco"),
        ("Sn", "Límite de fatiga corregido Sn = Cb·Cs·Cr·Co·Sn'", None, "MPa", "f1", "Bavaresco / PDF 7-A"),
        ("Salt", "Esfuerzo alterno base para Soderberg", f"=IF({A['Su']}<=199000*0.00689476,0.5*{A['Su']},99500*0.00689476)", "MPa", "f1",
         "PDF 7-A: 0.5 Su, con tope de 99 500 psi"),
        ("Ssd", "Esfuerzo cortante permisible Ssd = mín(0.30 Sy; 0.18 Su)", f"=MIN(0.3*{A['Sy']},0.18*{A['Su']})", "MPa", "f1", "ASME"),
    ]
    for k, lab, f, uni, est, nota in derivados:
        if k == "Sn":
            f = f"={A['Cb']}*{A['Cs']}*{A['Cr']}*{A['Co']}*{A['Snp']}"
        hDat.set(fila, 1, lab, "celda"); hDat.set(fila, 2, f, est); hDat.set(fila, 3, uni, "celda"); hDat.set(fila, 4, nota, "celda")
        A[k] = f"Datos!$B${fila}"
        fila += 1
    fila += 1
    hDat.set(fila, 1, "Constantes: 1 in = 25.4 mm; 1 pie = 304.8 mm; Kb = 0.869·d^-0.097 (d en pulgadas; 1 si d ≤ 0.3 in).", "nota1")
    for j, w in enumerate((52, 14, 10, 70), 1):
        hDat.ancho(j, w)

    # ============================================================ SECCIONES
    hSec.set(1, 1, "Secciones críticas: esfuerzos, ASME, Von Mises y Soderberg", "titulo")
    hSec.set(2, 1, "My, Mz, T, N: solicitaciones del modelo de elementos finitos de la memoria (datos). Esfuerzos y factores: fórmulas vivas. "
                   "Unidades: mm, N, N·mm, MPa.", "nota1")
    cols = ["Sección", "x [mm]", "d [mm]", "di [mm]", "Kf", "α (col.)", "Red. Ssd", "My [N·mm]", "Mz [N·mm]", "T [N·mm]", "N [N]",
            "M = √(My²+Mz²) [N·mm]", "K = di/d", "1 - K⁴",
            "σ flexión [MPa]", "σ axial [MPa]", "τ torsión [MPa]", "σ' Von Mises [MPa]", "FS estático",
            "√ ASME [N·mm]", "τ máx ASME [MPa]", "Ssd sección [MPa]", "ASME", "d req. ASME [mm]",
            "√ VM", "N Von Mises", "Von Mises", "d req. VM [mm]",
            "Kb", "Se [MPa]", "√ Sod", "N Soderberg", "Soderberg", "d req. Sod [mm]", "d requerido [mm]", "τ/Ssd"]
    H0 = 4
    for j, t in enumerate(cols, 1):
        hSec.set(H0, j, t, "enc")
    hSec.altos[H0] = 42
    n = len(c.secs)
    r1 = H0 + 1
    rN = H0 + n
    for i, s in enumerate(c.secs):
        r = r1 + i
        R = lambda col: ref(col, r)          # referencia a la celda de la columna en esta fila
        fR = s.res["Ssd"] / c.Ssd if c.Ssd else 1.0
        hSec.set(r, 1, s.nombre, "celda")
        for j, (v, est) in enumerate(((s.x, "in1"), (s.d, "in1"), (s.di, "in1"), (s.Kf, "in2"), (s.res["alfa"], "in3"), (fR, "in2"),
                                      (s.My, "in1"), (s.Mz, "in1"), (s.T, "in1"), (s.N, "in1")), 2):
            hSec.set(r, j, v, est)
        x, dd, di, Kf, al, fr, My, Mz, T, N = (R(k) for k in range(2, 12))
        M, K, f4 = R(12), R(13), R(14)
        f = {
            12: f"=SQRT({My}^2+{Mz}^2)",
            13: f"=IF({dd}=0,0,{di}/{dd})",
            14: f"=1-{K}^4",
            15: f"=32*{M}/(PI()*{dd}^3*{f4})",
            16: f"=IF({N}=0,0,{N}/(PI()/4*{dd}^2*(1-{K}^2)))",
            17: f"=16*ABS({T})/(PI()*{dd}^3*{f4})",
            18: f"=SQRT((ABS({R(15)})+ABS({R(16)}))^2+3*{R(17)}^2)",
            19: f"=IF({R(18)}=0,9999,{A['Sy']}/{R(18)})",
            20: f"=SQRT(({al}*ABS({N})*{dd}*(1+{K}^2)/8+{A['Cm']}*{M})^2+({A['Ct']}*ABS({T}))^2)",
            21: f"=16/(PI()*{dd}^3*{f4})*{R(20)}",
            22: f"={A['Ssd']}*{fr}",
            23: f'=IF({R(21)}<={R(22)},"OK","REVISAR")',
            24: f"=(16/(PI()*{R(22)}*{f4})*{R(20)})^(1/3)",
            25: f"=SQRT(({Kf}*{M}/({A['Sn']}*IF({A['tvm']}=1,{R(29)},1)))^2+0.694*(ABS({T})/{A['Sy']})^2)",
            26: f"=IF({R(25)}=0,9999,PI()*{dd}^3*{f4}/(32*{R(25)}))",
            27: f'=IF({R(26)}>={A["Nvm"]},"OK","REVISAR")',
            28: f"=(10.19*{A['Nvm']}*{R(25)}/{f4})^(1/3)",
            29: f"=IF({dd}/25.4<=0.3,1,0.869*({dd}/25.4)^-0.097)",
            30: f"={A['Salt']}*{A['Cs']}*{R(29)}*{A['Cr']}*{A['Cb']}*(1/{Kf})*{A['kfd']}",
            31: f"=SQRT((ABS({T})/{A['Sy']})^2+({M}/{R(30)})^2)",
            32: f"=IF({R(31)}=0,9999,PI()*{dd}^3*{f4}/(32*{R(31)}))",
            33: f'=IF({R(32)}>={A["Nsod"]},"OK","REVISAR")',
            34: f"=(32*{A['Nsod']}/(PI()*{f4})*{R(31)})^(1/3)",
            35: f"=MAX({R(24)},{R(28)},{R(34)})",
            36: f"={R(21)}/{R(22)}",
        }
        for col, fx in f.items():
            est = "estado" if col in (23, 27, 33) else ("f3" if col in (13, 14, 29) else ("f2" if col in (19, 26, 32, 36) else "f1"))
            hSec.set(r, col, fx, est)
    for col in (23, 27, 33):
        hSec.cond.append(f"{ref(col, r1)}:{ref(col, rN)}")
    hSec.ancho(1, 30)
    for j in range(2, len(cols) + 1):
        hSec.ancho(j, 12)
    hSec.congelar = (H0 + 1, 2)
    nt = rN + 2
    hSec.set(nt, 1, "Notas", "negrita")
    notas = [
        "α = 1 si no hay compresión axial; en compresión es el coeficiente de columna del programa (tabla 9.4).",
        "Red. Ssd = 0.75 si la sección tiene chavetero u hombro (según archivo de datos); si no, 1.",
        "ASME: τ = 16/(π d³ (1-K⁴))·√[(α Fa d (1+K²)/8 + Cm M)² + (Ct T)²] ≤ Ssd.",
        "Von Mises (Bavaresco ec. 19): N = π d³ (1-K⁴) / (32 √[(Kf M/Sn)² + 0.694 (T/Sy)²]); Sn se multiplica por Kb si 'Kb también en Von Mises' = 1.",
        "Soderberg (PDF 7-A): N = π d³ (1-K⁴) / (32 √[(T/Sy)² + (M/Se)²]),  Se = σalt·Cs·Kb·Cr·Cb·(1/Kf)·kf_div.",
        "d requerido: diámetro mínimo que cumple el criterio con las mismas solicitaciones (no recalcula el modelo de elementos finitos).",
    ]
    for k, t in enumerate(notas, 1):
        hSec.set(nt + k, 1, t, "nota1")

    def rng(col):
        return f"Secciones!${_L(col)}${r1}:${_L(col)}${rN}"

    # ============================================================ TORSION
    hTor.set(1, 1, "Torsión: ángulo de giro y límite", "titulo")
    hTor.set(2, 1, "Intervalos de eje de diámetro y torsor constantes. θ = Σ T·L / (G·J). Solo cuentan los intervalos con torque.", "nota1")
    tcols = ["x inicial [mm]", "x final [mm]", "L [mm]", "D [mm]", "di [mm]", "T [N·mm]", "J [mm⁴]", "θ [°]", "L con torque [mm]", "D con torque [mm]"]
    for j, t in enumerate(tcols, 1):
        hTor.set(4, j, t, "enc")
    hTor.altos[4] = 30
    xs = sorted({0.0, e.longitud} | {t.x0 for t in e.tramos} | {t.x1 for t in e.tramos}
                | {cg.x for cg in e.cargas if abs(cg.T) > EPS} | ({c.x_salida} if c.x_salida is not None else set()))
    xs = [x for x in xs if -EPS <= x <= e.longitud + EPS]
    ints = []
    for a, b in zip(xs, xs[1:]):
        if b - a < 0.01:
            continue
        xm = (a + b) / 2
        ints.append((a, b, e.D(xm), e.di(xm), c._internos(xm, -1)[4]))
    t1 = 5
    for i, (a, b, D, di, T) in enumerate(ints):
        r = t1 + i
        hTor.set(r, 1, a, "in1"); hTor.set(r, 2, b, "in1"); hTor.set(r, 3, f"={ref(2, r)}-{ref(1, r)}", "f1")
        hTor.set(r, 4, D, "in1"); hTor.set(r, 5, di, "in1"); hTor.set(r, 6, T, "in1")
        hTor.set(r, 7, f"=PI()/32*({ref(4, r)}^4-{ref(5, r)}^4)", "f0")
        hTor.set(r, 8, f"=DEGREES(ABS({ref(6, r)})*{ref(3, r)}/({A['G']}*{ref(7, r)}))", "f4")
        hTor.set(r, 9, f"=IF(ABS({ref(6, r)})>0.000001,{ref(3, r)},0)", "f1")
        hTor.set(r, 10, f'=IF(ABS({ref(6, r)})>0.000001,{ref(4, r)},"")', "f1")
    tN = t1 + len(ints) - 1
    q = tN + 2
    hTor.set(q, 1, "Ángulo de torsión θ [°]", "celdaneg"); hTor.set(q, 3, f"=SUM({ref(8, t1)}:{ref(8, tN)})", "f4")
    hTor.set(q + 1, 1, "Longitud sometida a torque L [mm]", "celdaneg"); hTor.set(q + 1, 3, f"=SUM({ref(9, t1)}:{ref(9, tN)})", "f1")
    hTor.set(q + 2, 1, "Diámetro menor con torque [mm]", "celdaneg"); hTor.set(q + 2, 3, f"=IF(C{q+1}=0,0,MIN({ref(10, t1)}:{ref(10, tN)}))", "f1")
    hTor.set(q + 3, 1, "θ admisible [°]", "celdaneg")
    hTor.set(q + 3, 3, f"=IF({A['minpie']}>0,{A['minpie']}/60*C{q+1}/304.8,IF(C{q+2}=0,0,C{q+1}/(20*C{q+2})))", "f4")
    hTor.set(q + 4, 1, "Estado", "celdaneg"); hTor.set(q + 4, 3, f'=IF(C{q}<=C{q+3},"OK","REVISAR")', "estado")
    hTor.set(q + 5, 1, "Factor mínimo para los diámetros del tramo", "celdaneg"); hTor.set(q + 5, 3, f"=IF(C{q+3}=0,0,(C{q}/C{q+3})^(1/4))", "f3")
    hTor.cond.append(f"C{q+4}:C{q+4}")
    for j, w in enumerate((30, 14, 14, 12, 12, 16, 16, 12, 16, 16), 1):
        hTor.ancho(j, w)
    TOR = dict(th=f"Torsion!$C${q}", thp=f"Torsion!$C${q+3}", est=f"Torsion!$C${q+4}", L=f"Torsion!$C${q+1}")

    # ============================================================ CASOS
    CAS = []
    if hCas is not None:
        hCas.set(1, 1, "Casos de carga adicionales: fluencia estática (Von Mises)", "titulo")
        hCas.set(2, 1, "My, Mz, T, N de cada caso: modelo de elementos finitos con las cargas escaladas (datos). FS = Sy / σ' (sin concentrador).", "nota1")
        cc = ["Sección", "d [mm]", "di [mm]", "My [N·mm]", "Mz [N·mm]", "T [N·mm]", "N [N]", "M [N·mm]", "σ flexión [MPa]",
              "σ axial [MPa]", "τ [MPa]", "σ' [MPa]", "FS", "Estado"]
        fila = 4
        for k in c.casos:
            c2 = k["calc"]
            hCas.set(fila, 1, f"Caso «{k['nombre']}»:  f_torque = {k['ft']:g},  f_radial = {k['fr']:g},  f_axial = {k['fa']:g},  FS mínimo = {k['fs']:g}", "subtitulo")
            fila += 1
            hCas.set(fila, 1, "FS mínimo exigido", "celdaneg"); hCas.set(fila, 2, k["fs"], "in2")
            fsr = f"$B${fila}"
            fila += 1
            for j, t in enumerate(cc, 1):
                hCas.set(fila, j, t, "enc")
            hCas.altos[fila] = 30
            fila += 1
            a0 = fila
            for s in c2.secs:
                r = fila
                hCas.set(r, 1, s.nombre, "celda")
                for j, (v, est) in enumerate(((s.d, "in1"), (s.di, "in1"), (s.My, "in1"), (s.Mz, "in1"), (s.T, "in1"), (s.N, "in1")), 2):
                    hCas.set(r, j, v, est)
                Rr = lambda col: ref(col, r)
                hCas.set(r, 8, f"=SQRT({Rr(4)}^2+{Rr(5)}^2)", "f1")
                kk = f"IF({Rr(2)}=0,0,{Rr(3)}/{Rr(2)})"
                hCas.set(r, 9, f"=32*{Rr(8)}/(PI()*{Rr(2)}^3*(1-{kk}^4))", "f1")
                hCas.set(r, 10, f"=IF({Rr(7)}=0,0,{Rr(7)}/(PI()/4*{Rr(2)}^2*(1-{kk}^2)))", "f1")
                hCas.set(r, 11, f"=16*ABS({Rr(6)})/(PI()*{Rr(2)}^3*(1-{kk}^4))", "f1")
                hCas.set(r, 12, f"=SQRT((ABS({Rr(9)})+ABS({Rr(10)}))^2+3*{Rr(11)}^2)", "f1")
                hCas.set(r, 13, f"=IF({Rr(12)}=0,9999,{A['Sy']}/{Rr(12)})", "f2")
                hCas.set(r, 14, f'=IF({Rr(13)}>={fsr},"OK","REVISAR")', "estado")
                fila += 1
            hCas.cond.append(f"N{a0}:N{fila-1}")
            CAS.append((k, f"Casos!$M${a0}:$M${fila-1}", f"Casos!$A${a0}:$A${fila-1}"))
            fila += 2
        hCas.ancho(1, 34)
        for j in range(2, 15):
            hCas.ancho(j, 13)

    # ============================================================ RESUMEN
    hRes.set(1, 1, f"Verificación de cálculo – {e.nombre}", "titulo")
    hRes.set(2, 1, "Libro de verificación con fórmulas vivas. Compara lo que calcula este libro con los valores del programa (memoria PDF).", "nota1")
    heads = ["Criterio", "Sección / lugar", "Valor (este libro)", "Límite", "Estado", "Valor (memoria)", "Dif. %"]
    for j, t in enumerate(heads, 1):
        hRes.set(4, j, t, "enc")
    hRes.altos[4] = 30
    P = {cr["nombre"]: cr for cr in c.criterios}
    rr = 5
    nom = lambda col: f"INDEX({rng(1)},MATCH(C{rr},{rng(col)},0))"
    vm_mem = min(s.res["N_vm"] for s in c.secs)
    sod_mem = min(s.res["N_sod"] for s in c.secs)
    asme_mem = max(s.res["tau_asme"] / s.res["Ssd"] for s in c.secs)
    filas = [
        ("Fatiga – Von Mises (N mínimo)", f"=INDEX({rng(1)},MATCH(C{rr},{rng(26)},0))", f"=MIN({rng(26)})", f"={A['Nvm']}", "ge", vm_mem, "f2"),
        ("Fatiga – Soderberg (N mínimo)", f"=INDEX({rng(1)},MATCH(C{rr+1},{rng(32)},0))", f"=MIN({rng(32)})", f"={A['Nsod']}", "ge", sod_mem, "f2"),
        ("Resistencia – ASME (τ máx / Ssd)", f"=INDEX({rng(1)},MATCH(C{rr+2},{rng(36)},0))", f"=MAX({rng(36)})", "=1", "le", asme_mem, "f3"),
        ("Rigidez torsional θ [°]", "Suma de tramos a torsión (la memoria verifica además cada tramo)", f"={TOR['th']}", f"={TOR['thp']}", "le", (c.tors.get("th_tot", c.tors["th"]) if c.tors else 0.0), "f4"),
    ]
    for lab, sec, val, lim, tipo, mem, est in filas:
        hRes.set(rr, 1, lab, "celda"); hRes.set(rr, 2, sec, "celda")
        hRes.set(rr, 3, val, est); hRes.set(rr, 4, lim, est)
        hRes.set(rr, 5, f'=IF(C{rr}{">=" if tipo == "ge" else "<="}D{rr},"OK","REVISAR")', "estado")
        hRes.set(rr, 6, mem, "in" + est[1])
        hRes.set(rr, 7, f"=IF(F{rr}=0,0,(C{rr}/F{rr}-1)*100)", "f2")
        rr += 1
    # criterios del modelo de elementos finitos: se copian como datos (no recalculables en la hoja)
    fe = [(cr["nombre"], cr) for cr in c.criterios if cr["nombre"].startswith(("Rigidez lateral", "Pendiente"))]
    for nombre, cr in fe:
        v = float(cr["valor"].split("=")[1].split()[0].replace("°", ""))
        l = float(cr["lim"].replace("≤", "").replace("mm", "").strip())
        hRes.set(rr, 1, nombre + " (del modelo FE)", "celda"); hRes.set(rr, 2, cr["sec"], "celda")
        hRes.set(rr, 3, v, "in4"); hRes.set(rr, 4, l, "in4")
        hRes.set(rr, 5, f'=IF(C{rr}<=D{rr},"OK","REVISAR")', "estado")
        hRes.set(rr, 6, v, "in4"); hRes.set(rr, 7, f"=IF(F{rr}=0,0,(C{rr}/F{rr}-1)*100)", "f2")
        rr += 1
    for k, rg, rn in CAS:
        mem = k["FS"]
        hRes.set(rr, 1, f"Caso «{k['nombre']}» – FS mínimo", "celda")
        hRes.set(rr, 2, f"=INDEX({rn},MATCH(C{rr},{rg},0))", "celda")
        hRes.set(rr, 3, f"=MIN({rg})", "f2"); hRes.set(rr, 4, k["fs"], "in2")
        hRes.set(rr, 5, f'=IF(C{rr}>=D{rr},"OK","REVISAR")', "estado")
        hRes.set(rr, 6, mem, "in2"); hRes.set(rr, 7, f"=IF(F{rr}=0,0,(C{rr}/F{rr}-1)*100)", "f2")
        rr += 1
    hRes.cond.append(f"E5:E{rr-1}")
    hRes.set(rr + 1, 1, "Conclusión global", "celdaneg")
    hRes.set(rr + 1, 2, f'=IF(COUNTIF(E5:E{rr-1},"REVISAR")=0,"OK","REVISAR")', "estado")
    hRes.cond.append(f"B{rr+1}:B{rr+1}")
    hRes.set(rr + 3, 1, "Cómo leer este libro", "negrita")
    for k, t in enumerate([
        "Azul sobre amarillo: datos (material, factores, solicitaciones del modelo FE). Negro: fórmulas.",
        "Hoja Secciones: cada columna es un paso del cálculo, con la fórmula en las notas al pie.",
        "Dif. %: diferencia entre este libro y la memoria PDF. Debe ser ~0 %; si no, cambió algún dato o factor.",
        "La rigidez lateral y la pendiente salen del modelo de elementos finitos y se copian como datos (no se pueden recalcular aquí).",
        "Si cambia un diámetro, hay que volver a ejecutar el programa para actualizar My, Mz, T y N en las hojas.",
    ], 1):
        hRes.set(rr + 3 + k, 1, t, "nota1")
    for j, w in enumerate((62, 30, 18, 14, 12, 18, 10), 1):
        hRes.ancho(j, w)
    lib.guardar(ruta)


def _L(n):
    from xlsxmin import _col
    return _col(n)
