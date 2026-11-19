"""Escritura de la memoria de cálculo del eje en LaTeX (diagramas con pgfplots/TikZ)."""
import datetime
import math
import os

_UNI = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
        ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")]
_SIM = {"τ": r"$\tau$", "θ": r"$\theta$", "α": r"$\alpha$", "σ": r"$\sigma$", "≥": r"$\geq$",
        "≤": r"$\leq$", "·": r"$\cdot$", "µ": r"$\mu$", "°": r"$^\circ$", "–": "--", "×": r"$\times$"}


def tx(s):
    s = str(s)
    for a, b in _UNI:
        s = s.replace(a, b)
    for a, b in _SIM.items():
        s = s.replace(a, b)
    return s


def n(v, d=2):
    if v is None:
        return "--"
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return r"$\infty$"
    return f"{v:,.{d}f}".replace(",", r"\,")


def ok(b):
    return r"\textcolor{verde}{\textbf{OK}}" if b else r"\textcolor{rojo}{\textbf{REVISAR}}"


def _coords(pts, key, fy=1.0, fx=1.0):
    out, last = [], None
    for p in pts:
        c = (round(p["x"] * fx, 3), round(p[key] * fy, 6))
        if c != last:
            out.append(f"({c[0]},{c[1]})")
        last = c
    return " ".join(out)


def _diagrama(pts, key, fy, ylabel, color, L):
    return rf"""
\begin{{tikzpicture}}
\begin{{axis}}[width=\textwidth, height=4.2cm, xmin=0, xmax={L:g}, grid=major, grid style={{gray!25}},
  xlabel={{$x$ [mm]}}, ylabel={{{ylabel}}}, ylabel style={{font=\small}}, xlabel style={{font=\small}},
  tick label style={{font=\footnotesize}}, scaled y ticks=false,
  yticklabel style={{/pgf/number format/fixed}}]
\addplot[draw={color}, fill={color}!18, thick] coordinates {{(0,0) {_coords(pts, key, fy)} ({L:g},0)}} \closedcycle;
\end{{axis}}
\end{{tikzpicture}}"""


def _esquema(c):
    e = c.eje
    L = e.longitud
    Dmax = max(max(t.D1, t.D2) for t in e.tramos)
    sx = 15.0 / L
    sy = min(2.2 / Dmax, sx * 2.5)
    X = lambda x: x * sx
    Y = lambda y: y * sy
    o = [r"\begin{tikzpicture}[line join=round]"]
    for t in e.tramos:
        o.append(rf"\filldraw[fill=gray!20, draw=black, thick] ({X(t.x0):.3f},{Y(-t.D1/2):.3f}) -- "
                 rf"({X(t.x1):.3f},{Y(-t.D2/2):.3f}) -- ({X(t.x1):.3f},{Y(t.D2/2):.3f}) -- "
                 rf"({X(t.x0):.3f},{Y(t.D1/2):.3f}) -- cycle;")
        o.append(rf"\node[font=\scriptsize] at ({X((t.x0+t.x1)/2):.3f},0) {{\O{t.D1:g}}};")
    for h in e.huecos:
        o.append(rf"\draw[dashed] ({X(h.x0):.3f},{Y(-h.D1/2):.3f}) rectangle ({X(h.x1):.3f},{Y(h.D2/2):.3f});")
    o.append(rf"\draw[dash dot, gray] (-0.3,0) -- ({X(L)+0.3:.3f},0);")
    yb = Y(-Dmax / 2)
    for k, a in enumerate(e.apoyos, 1):
        x = X(a.x)
        o.append(rf"\draw[thick, fill=white] ({x:.3f},{yb:.3f}) -- ({x-0.22:.3f},{yb-0.38:.3f}) -- ({x+0.22:.3f},{yb-0.38:.3f}) -- cycle;")
        if a.fijo_axial:
            o.append(rf"\draw[thick] ({x-0.3:.3f},{yb-0.38:.3f}) -- ({x+0.3:.3f},{yb-0.38:.3f});")
            for j in range(4):
                xx = x - 0.27 + j * 0.18
                o.append(rf"\draw ({xx:.3f},{yb-0.38:.3f}) -- ({xx-0.1:.3f},{yb-0.5:.3f});")
        o.append(rf"\node[font=\scriptsize, below] at ({x:.3f},{yb-0.55:.3f}) {{A{k}}};")
    yt = Y(Dmax / 2)
    for c_ in e.cargas:
        x = X(c_.x)
        F = math.hypot(c_.Fy, c_.Fz)
        Ft = f"{F:,.0f}".replace(",", r"\,")
        if F > 1e-6:
            o.append(rf"\draw[-latex, very thick, red!70!black] ({x:.3f},{yt+1.0:.3f}) -- ({x:.3f},{yt+0.05:.3f});")
            o.append(rf"\node[font=\scriptsize, red!70!black, above] at ({x:.3f},{yt+1.0:.3f}) {{$F={Ft}$ N}};")
        if abs(c_.T) > 1e-6:
            o.append(rf"\draw[-latex, thick, blue!70!black] ({x-0.25:.3f},{yt+0.25:.3f}) arc (160:20:0.27);")
            o.append(rf"\node[font=\scriptsize, blue!70!black, right] at ({x+0.25:.3f},{yt+0.3:.3f}) {{$T_{{entrada}}={abs(c_.T)/1000:,.1f}$ N$\cdot$m}};")
        if abs(c_.qy) + abs(c_.qz) > 1e-9 and c_.Lq > 0:
            o.append(rf"\draw[red!70!black] ({x:.3f},{yt+0.5:.3f}) rectangle ({X(c_.x+c_.Lq):.3f},{yt+0.2:.3f});")
    if c.x_salida is not None:
        x = X(c.x_salida)
        o.append(rf"\draw[-latex, thick, blue!70!black] ({x+0.25:.3f},{Y(Dmax/2)+0.25:.3f}) arc (20:160:0.27);")
        o.append(rf"\node[font=\scriptsize, blue!70!black, right] at ({x+0.25:.3f},{Y(Dmax/2)+0.3:.3f}) {{$T_{{salida}}$}};")
    # cotas
    yd = yb - 1.0
    marcas = sorted({0.0, L} | {t.x1 for t in e.tramos})
    for a, b in zip(marcas, marcas[1:]):
        o.append(rf"\draw[latex-latex, thin] ({X(a):.3f},{yd:.3f}) -- node[below, font=\scriptsize] {{{b-a:g}}} ({X(b):.3f},{yd:.3f});")
    for m in marcas:
        o.append(rf"\draw[thin, gray] ({X(m):.3f},{yd-0.1:.3f}) -- ({X(m):.3f},{yb:.3f});")
    o.append(rf"\draw[latex-latex, thin] (0,{yd-0.7:.3f}) -- node[below, font=\scriptsize] {{{L:g}}} ({X(L):.3f},{yd-0.7:.3f});")
    o.append(r"\end{tikzpicture}")
    return "\n".join(o)


def _sn(c, s):
    Su, Se = c.Su, s.res["Se"]
    sw = s.res["sb"]
    return rf"""
\begin{{tikzpicture}}
\begin{{loglogaxis}}[width=0.82\textwidth, height=6cm, xmin=1e3, xmax=1e8, ymin={min(Se, sw, 0.5*Su)*0.5:.2f}, ymax={Su*1.1:.2f},
  xlabel={{Número de ciclos $N$}}, ylabel={{Esfuerzo [MPa]}}, grid=major, grid style={{gray!25}},
  legend style={{font=\scriptsize, at={{(0.02,0.02)}}, anchor=south west}}, tick label style={{font=\footnotesize}},
  log basis y=10, yticklabel style={{/pgf/number format/fixed}}]
\addplot[very thick, black] coordinates {{(1e3,{0.9*Su:.3f}) (1e6,{Se:.3f}) (1e8,{Se:.3f})}};
\addlegendentry{{Curva S--N corregida}}
\addplot[dashed, blue] coordinates {{(1e3,{0.5*Su:.3f}) (1e8,{0.5*Su:.3f})}};
\addlegendentry{{Probeta $0.5\,S_u = {0.5*Su:.1f}$ MPa}}
\addplot[densely dotted, very thick, green!50!black] coordinates {{(1e3,{Se:.3f}) (1e8,{Se:.3f})}};
\addlegendentry{{Límite corregido $S_e = {Se:.1f}$ MPa}}
\addplot[thick, red] coordinates {{(1e3,{max(sw,1e-3):.4f}) (1e8,{max(sw,1e-3):.4f})}};
\addlegendentry{{Esfuerzo de trabajo $\sigma = {sw:.2f}$ MPa}}
\end{{loglogaxis}}
\end{{tikzpicture}}"""


def generar(c, ruta_tex):
    e, d = c.eje, c.dat
    P = lambda k: tx(d.s("proyecto", k))
    desig = d.s("proyecto", "designacion_eje") or e.nombre
    titulo = tx(desig if desig.lower().startswith("eje") else "Eje " + desig)
    L = e.longitud
    fecha = datetime.date.today().strftime("%d/%m/%Y")
    logo = d.s("proyecto", "logo")
    if logo and os.path.exists(logo):
        logo_tex = rf"\includegraphics[height=2.4cm,keepaspectratio]{{{logo.replace(os.sep, '/')}}}"
    else:
        logo_tex = r"\fbox{\parbox[c][2.2cm][c]{5cm}{\centering\color{gray} LOGO}}"
    rpm = d.f("operacion", "rpm")
    Tmax = max((abs(p["T"]) for p in c.diag), default=0.0)
    pot = Tmax / 1000 * rpm * 2 * math.pi / 60 / 1000  # kW
    S = []
    w = S.append

    w(r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\IfFileExists{spanish.ldf}{\usepackage[spanish,es-nodecimaldot,es-tabla]{babel}}{%
  \usepackage[english]{babel}\addto\captionsenglish{\renewcommand{\contentsname}{Índice}%
  \renewcommand{\tablename}{Tabla}\renewcommand{\figurename}{Figura}\renewcommand{\appendixname}{Anexo}}}
\usepackage[a4paper,margin=2.3cm,headheight=28pt]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,longtable,array,tabularx}
\usepackage[table]{xcolor}
\usepackage{graphicx}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.16}
\usepackage{fancyhdr,lastpage}
\usepackage{float}
\usepackage[font=small,labelfont=bf]{caption}
\usepackage[hidelinks]{hyperref}
\definecolor{verde}{RGB}{0,128,60}
\definecolor{rojo}{RGB}{200,30,30}
\definecolor{azul}{RGB}{20,60,120}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\renewcommand{\arraystretch}{1.15}
\pagestyle{fancy}
\fancyhf{}""")
    w(rf"\lhead{{\small {P('empresa')}}}")
    w(rf"\chead{{\small Memoria de cálculo -- {titulo}}}")
    w(rf"\rhead{{\small {P('codigo_documento')} -- Rev. {P('revision')}}}")
    w(r"\cfoot{\small Página \thepage\ de \pageref{LastPage}}")
    w(r"\begin{document}")
    # ---------------- carátula
    w(rf"""\begin{{titlepage}}
\centering
{logo_tex}\par\vspace{{2.5cm}}
{{\Large\bfseries {P('empresa')}\par}}\vspace{{1.2cm}}
{{\Huge\bfseries\color{{azul}} MEMORIA DE CÁLCULO\par}}\vspace{{0.4cm}}
{{\LARGE\bfseries {titulo}\par}}\vspace{{0.4cm}}
{{\large Verificación por resistencia, fatiga y rigidez\par}}\vspace{{2cm}}
\begin{{tabular}}{{>{{\bfseries}}l l}}
Proyecto: & {P('proyecto')}\\
Cliente: & {P('cliente')}\\
Documento: & {P('codigo_documento')}\\
Revisión: & {P('revision')}\\
Fecha: & {fecha}\\
\end{{tabular}}
\vfill
\begin{{tabular}}{{|p{{4.2cm}}|p{{4.2cm}}|p{{4.2cm}}|}}\hline
\textbf{{Elaborado}} & \textbf{{Revisado}} & \textbf{{Aprobado}}\\
{P('elaborado')} & {P('revisado')} & {P('aprobado')}\\[1.2cm]\hline
\end{{tabular}}
\end{{titlepage}}
\tableofcontents
\newpage""")

    # ---------------- 1 objeto
    w(rf"""\section{{Objeto y alcance}}
Esta memoria verifica el eje «{tx(desig)}» por resistencia, fatiga y rigidez. La geometría, el material,
los apoyos y las cargas provienen del modelo del eje en el generador de ejes de Autodesk Inventor. Los
parámetros de servicio (velocidad, tipo de carga, confiabilidad y límites de rigidez) son datos de diseño.

El alcance se limita al eje. No incluye la selección de rodamientos, soportes, chavetas ni elementos montados.

\section{{Documentos de referencia}}
\begin{{itemize}}
\item Cálculo de ejes de transmisión y de máquinas (Cap.~7-A): fórmula de la ASME para el esfuerzo cortante
máximo, rigidez lateral y torsional, fatiga de Soderberg con factores de corrección (Shigley, Faires, Hori, Halowenko).
\item G. Bavaresco, \emph{{Procedimiento para el diseño de ejes}}: fatiga por Von Mises (ANSI B106.1M, ec.~19),
factores $C_b$, $C_s$, $C_r$, $C_o$ y concentración de esfuerzos $K_f$.
\item CEMA, \emph{{Belt Conveyors for Bulk Materials}}, cap.~8: límite de pendiente del eje (fig.~8.11).
\end{{itemize}}
""")

    # ---------------- 3 datos
    w(r"\section{Datos de entrada}")
    w(r"\subsection{Geometría del eje}")
    w(r"\begin{figure}[H]\centering" + _esquema(c) +
      r"\caption{Esquema del eje, apoyos y cargas (cotas en mm; escala vertical ampliada).}\end{figure}")
    w(r"""\begin{table}[H]\centering\caption{Tramos del eje.}
\begin{tabular}{c l r r r r}\toprule
Tramo & Tipo & $x_{ini}$ [mm] & $x_{fin}$ [mm] & $L$ [mm] & $\varnothing$ [mm]\\\midrule""")
    for t in e.tramos:
        dtxt = n(t.D1, 1) if abs(t.D1 - t.D2) < 1e-9 else f"{n(t.D1,1)} -- {n(t.D2,1)}"
        w(rf"{t.idx} & {tx(t.tipo)} & {n(t.x0,1)} & {n(t.x1,1)} & {n(t.L,1)} & {dtxt}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    if e.huecos:
        w("El eje es hueco en: " + "; ".join(
            f"{n(h.x0,1)}--{n(h.x1,1)} mm ($d_i$ = {n(h.D1,1)} mm)" for h in e.huecos) + ".")
    ops = [o for o in e.operaciones if o.tipo != "Chaflán"]
    if ops:
        w(r"\begin{table}[H]\centering\caption{Detalles que concentran esfuerzos.}\begin{tabular}{l c r l}\toprule "
          r"Detalle & Tramo & $x$ [mm] & Dato\\\midrule")
        for o in ops:
            dato = f"R = {o.R:g} mm" if o.tipo == "Empalme" else (f"L = {o.x1-o.x0:g} mm" if o.x1 > o.x0 else "")
            w(rf"{tx(o.tipo)} & {o.tramo} & {n(o.x0,1)} & {dato}\\")
        w(r"\bottomrule\end{tabular}\end{table}")
    masa = sum(el["A"] * (el["b"] - el["a"]) for el in c.elem) * c.rho * 1e-9
    w(rf"Longitud total: {n(L,1)} mm. Masa del eje: {n(masa,2)} kg.")

    w(r"\subsection{Material}")
    w(rf"""\begin{{table}}[H]\centering\caption{{Propiedades del material.}}\begin{{tabular}}{{l r}}\toprule
Material & {tx(c.mat_nombre)}\\
Resistencia a la tracción $S_u$ & {n(c.Su,1)} MPa\\
Límite de fluencia $S_y$ & {n(c.Sy,1)} MPa\\
Módulo de elasticidad $E$ & {n(c.E,0)} MPa\\
Módulo de corte $G$ & {n(c.G,0)} MPa\\
Densidad $\rho$ & {n(c.rho,0)} kg/m$^3$\\
Estado (factor $C_o$) & {tx(d.s('material','estado'))}\\\bottomrule\end{{tabular}}\end{{table}}""")

    w(r"\subsection{Apoyos}")
    w(r"\begin{table}[H]\centering\caption{Apoyos radiales del eje.}\begin{tabular}{c r l}\toprule "
      r"Apoyo & $x$ [mm] & Tipo\\\midrule")
    for k, a in enumerate(e.apoyos, 1):
        w(rf"A{k} & {n(a.x,1)} & {'fijo (toma carga axial)' if a.fijo_axial else 'libre axialmente'}\\")
    w(r"\bottomrule\end{tabular}\end{table}")

    w(r"\subsection{Cargas}")
    w(r"\begin{table}[H]\centering\caption{Cargas aplicadas al eje.}\begin{tabular}{r r r r r r r r}\toprule "
      r"$x$ [mm] & $F_y$ [N] & $F_z$ [N] & $F_r$ [N] & $\theta$ [$^\circ$] & $F_x$ axial [N] & $q$ [N/mm] & $T$ [N$\cdot$m]\\\midrule")
    for c_ in e.cargas:
        q = math.hypot(c_.qy, c_.qz)
        Fr = math.hypot(c_.Fy, c_.Fz)
        th = math.degrees(math.atan2(c_.Fz, c_.Fy)) if Fr > 1e-9 else 0.0
        w(rf"{n(c_.x,1)} & {n(c_.Fy,1)} & {n(c_.Fz,1)} & {n(Fr,1) if Fr > 1e-9 else '--'} & {n(th,1) if Fr > 1e-9 else '--'} & {n(c_.Fx,1)} & {n(q,3) if q else '--'} & {n(c_.T/1000,2) if c_.T else '--'}\\")
    if c.x_salida is not None:
        w(rf"{n(c.x_salida,1)} & -- & -- & -- & -- & -- & -- & {n(c.torques[-1][1]/1000,2)} (salida)\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    w(("Se incluye el peso propio del eje como carga distribuida." if c.con_peso else
       "No se incluye el peso propio del eje.") +
      rf" Velocidad de giro: {n(rpm,1)} rpm. Torque máximo: {n(Tmax/1000,2)} N$\cdot$m"
      + (rf", potencia transmitida $P = T\,\omega$ = {n(pot,2)} kW." if Tmax else "."))

    w(r"\subsection{Parámetros de diseño}")
    w(rf"""\begin{{table}}[H]\centering\caption{{Parámetros de diseño.}}\begin{{tabularx}}{{\textwidth}}{{l X}}\toprule
Tipo de carga (ASME) & {tx(c.asme_desc)}: $C_m$ = {c.Cm:g}, $C_t$ = {c.Ct:g}\\
Factor de seguridad Von Mises & $N$ = {c.N_vm:g}\\
Factor mínimo Soderberg & $N_{{mín}}$ = {c.N_sod:g}\\
Confiabilidad & {tx(d.s('fatiga','confiabilidad'))} \% ($B$ = {c.B:g})\\
Temperatura & {tx(d.s('fatiga','temperatura'))} $^\circ$C\\
Chavetero & {tx(d.s('fatiga','chavetero'))} ($K_f$ = {d.kf_chavetero():g})\\
Flecha permisible & {tx(c.flecha_desc)}\\
Torsión permisible & {tx(d.torsion()[0])}\\
Pendiente máxima en puntos de carga & $\tan\alpha$ = {c.tan_lim:g}\\\bottomrule\end{{tabularx}}\end{{table}}""")

    # ---------------- 4 análisis
    w(r"\section{Análisis de cargas}")
    w(r"\subsection{Modelo de cálculo}")
    w(r"El eje se modela como viga escalonada sobre apoyos simples, por elementos finitos"
      + (rf" con deformación por cortante (Timoshenko, $\beta$ = {c.beta:g})" if c.beta else " (Euler-Bernoulli)")
      + rf", en los planos XY y XZ, con {len(c.elem)} elementos. El momento flector resultante es "
      r"$M=\sqrt{M_y^2+M_z^2}$. El torque recorre solo el tramo entre su entrada y su salida.")
    w(r"\subsection{Reacciones}")
    w(r"\begin{table}[H]\centering\caption{Reacciones en los apoyos y comparación con el generador de ejes.}"
      r"\begin{tabular}{c r r r r r r}\toprule Apoyo & $x$ [mm] & $R_y$ [N] & $R_z$ [N] & $R$ [N] & $R$ Inventor [N] & Dif. [\%]\\\midrule")
    difs = []
    for k, (a, ry, rz) in enumerate(zip(e.apoyos, c.Ry, c.Rz), 1):
        R = math.hypot(ry, rz)
        df = (R / a.F_inv - 1) * 100 if a.F_inv > 1e-6 else 0.0
        difs.append(abs(df))
        w(rf"A{k} & {n(a.x,1)} & {n(ry,1)} & {n(rz,1)} & {n(R,1)} & {n(a.F_inv,1)} & {n(df,2)}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    w(r"\subsection{Diagramas de esfuerzos internos}")
    w(r"\begin{figure}[H]\centering")
    w(_diagrama(c.diag, "Vy", 1.0, r"$V_y$ [N]", "blue", L))
    if c.hay_z:
        w(_diagrama(c.diag, "Vz", 1.0, r"$V_z$ [N]", "cyan!60!black", L))
    if c.hay_z:
        w(_diagrama(c.diag, "My", 1e-3, r"$M_y$ [N$\cdot$m]", "blue!70!black", L))
        w(_diagrama(c.diag, "Mz", 1e-3, r"$M_z$ [N$\cdot$m]", "cyan!60!black", L))
    w(_diagrama(c.diag, "M", 1e-3, r"$M$ resultante [N$\cdot$m]", "red", L))
    if c.hay_torque:
        w(_diagrama(c.diag, "T", 1e-3, r"$T$ [N$\cdot$m]", "green!50!black", L))
    if c.hay_axial:
        w(_diagrama(c.diag, "N", 1.0, r"$N$ [N]", "orange", L))
    w(r"\caption{Diagramas de cortante, momento flector resultante" + (", torsor" if c.hay_torque else "")
      + (" y fuerza axial" if c.hay_axial else "") + r".}\end{figure}")
    w(r"\subsection{Deformada}")
    w(r"\begin{figure}[H]\centering" + _diagrama(c.diag, "f", 1000.0, r"$y$ [$\mu$m]", "violet", L)
      + r"\caption{Flecha resultante a lo largo del eje.}\end{figure}")
    fmax = max(p["f"] for p in c.diag)
    sbmax = max(32 * p["M"] / (math.pi * e.D(p["x"]) ** 3 * (1 - (e.di(p["x"]) / e.D(p["x"])) ** 4)) for p in c.diag)
    w(r"\subsection{Comparación con el generador de ejes}")
    w(rf"""\begin{{table}}[H]\centering\caption{{Resultados propios frente a los del generador de ejes de Inventor.}}
\begin{{tabular}}{{l r r}}\toprule Resultado & Este cálculo & Inventor\\\midrule
Flecha máxima [$\mu$m] & {n(fmax*1000,3)} & {n(e.inv.flecha_max,3)}\\
Esfuerzo de flexión máximo [MPa] & {n(sbmax,3)} & {n(e.inv.sigma_max,3)}\\
Masa del eje [kg] & {n(masa,3)} & {n(e.inv.masa,3)}\\\bottomrule\end{{tabular}}\end{{table}}""")
    dif_f = abs(fmax * 1000 / e.inv.flecha_max - 1) * 100 if e.inv.flecha_max else 0
    concl4 = (rf"Las reacciones coinciden con las del generador de ejes con una diferencia máxima de {n(max(difs),2)} \% "
              rf"y la flecha máxima con {n(dif_f,2)} \%. El modelo de cálculo es consistente con el de Inventor.")
    if max(difs) > 2 or dif_f > 2:
        concl4 = (rf"Las reacciones difieren hasta {n(max(difs),2)} \% y la flecha {n(dif_f,2)} \% de las del "
                  r"generador de ejes. Conviene revisar que los resultados de Inventor estén actualizados.")
    if c.hay_torque and e.inv.tors_max == 0:
        concl4 += (r" El generador de ejes reporta torsión nula porque en el modelo el torsor no tiene salida definida; "
                   r"en esta memoria se considera según el supuesto indicado en el Anexo~A.")
    w(r"\subsection*{Conclusión}" + concl4)

    # ---------------- 5 secciones críticas
    w(r"\section{Secciones críticas}")
    w(r"Se evalúan los cambios de diámetro, los chaveteros y ranuras, los puntos de carga y el punto de máximo "
      r"momento de cada tramo. En los hombros se toma el diámetro menor.")
    w(r"\begin{table}[H]\centering\small\caption{Secciones críticas y solicitaciones (componentes por plano y resultante).}"
      r"\begin{tabular}{l r r r r r r r r r r}\toprule Sección & $x$ [mm] & $d$ [mm] & $K_f$ & $M_y$ & $M_z$ & $M$ & $\varphi$ [$^\circ$] & $V$ [N] & $T$ & $N$ [N]\\"
      r" & & & & [N$\cdot$m] & [N$\cdot$m] & [N$\cdot$m] & & & [N$\cdot$m] & \\\midrule")
    for s in c.secs:
        fi = math.degrees(math.atan2(s.Mz, s.My)) if s.M > 1e-6 else 0.0
        w(rf"{tx(s.nombre)} & {n(s.x,1)} & {n(s.d,1)} & {s.Kf:g} & {n(s.My/1000,2)} & {n(s.Mz/1000,2)} & {n(s.M/1000,2)} & {n(fi,1)} & {n(math.hypot(s.Vy,s.Vz),1)} & {n(abs(s.T)/1000,2)} & {n(s.N,1)}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    w(r"Convención: $M_y$ y $V_y$ actúan en el plano XY (carga a 0$^\circ$), $M_z$ y $V_z$ en el plano XZ (carga a 90$^\circ$); "
      r"los ángulos se miden de $+Y$ hacia $+Z$. $M=\sqrt{M_y^2+M_z^2}$ y $V=\sqrt{V_y^2+V_z^2}$ se calculan sección por sección "
      r"(no se suman los máximos de cada plano, que pueden ocurrir en secciones distintas). $\varphi=\mathrm{atan2}(M_z,M_y)$ es la orientación del plano de flexión. "
      r"Como el eje gira, el esfuerzo de flexión resultante es completamente alternante con amplitud $\sigma=32M/(\pi d^3)$ en cualquier orientación de la carga.")
    if getattr(c, "_nota_peterson", False):
        w(r"Valores de $K_f$: hombros con empalme, $K_f=1+q\,(K_t-1)$ con $K_t$ a flexión de Peterson (Shigley, tabla 7-1) según $r/d$ y $D/d$ "
          r"(en la tabla de secciones críticas); hombro con borde cortante 2.5 (Bavaresco); chavetero de perfil 1.6; "
          r"chavetero de patín 1.3; sección lisa 1.0.")
    else:
        w(r"Valores de $K_f$ (Bavaresco): hombro con borde redondeado 1.5; hombro con borde cortante 2.5; "
          r"chavetero de perfil 1.6; chavetero de patín 1.3; sección lisa 1.0.")

    # ---------------- 6 resistencia
    w(r"\section{Verificación por resistencia}")
    w(r"\subsection{Esfuerzos estáticos}")
    w(r"""\[\sigma = \frac{32M}{\pi d^3(1-K^4)} + \frac{4N}{\pi d^2(1-K^2)},\qquad
\tau = \frac{16T}{\pi d^3(1-K^4)},\qquad \sigma' = \sqrt{\sigma^2+3\tau^2},\qquad FS = \frac{S_y}{\sigma'}\]""")
    w(r"\begin{table}[H]\centering\small\caption{Esfuerzos estáticos (informativo).}"
      r"\begin{tabular}{l r r r r}\toprule Sección & $\sigma$ [MPa] & $\tau$ [MPa] & $\sigma'$ [MPa] & $FS$\\\midrule")
    for s in c.secs:
        r = s.res
        w(rf"{tx(s.nombre)} & {n(abs(r['sb'])+abs(r['sa']),2)} & {n(r['tau'],2)} & {n(r['svm'],2)} & {n(r['FS'],2)}\\")
    w(r"\bottomrule\end{tabular}\end{table}")

    w(r"\subsection{Fórmula de la ASME (máximo esfuerzo cortante)}")
    w(r"""\[\tau_{máx} = \frac{16}{\pi d^3(1-K^4)}\sqrt{\left[\frac{\alpha F_a d(1+K^2)}{8}+C_m M\right]^2+(C_t T)^2}\;\le\;S_{sd}\]""")
    w(rf"""Esfuerzo permisible: $S_{{sd}} = \min(0.30\,S_y;\ 0.18\,S_u) = \min({n(0.3*c.Sy,1)};\ {n(0.18*c.Su,1)}) = {n(c.Ssd,1)}$ MPa,
reducido al 75~\% ({n(0.75*c.Ssd,1)} MPa) en secciones con chavetero"""
      + (" u hombro." if d.s("asme", "reducir_en_hombros").lower().startswith("s") else ".")
      + rf" Factores de carga: $C_m$ = {c.Cm:g}, $C_t$ = {c.Ct:g}. "
      + ("Coeficiente de columna $\\alpha$ según la carga axial (tracción: 1)." if c.hay_axial else
         "No hay carga axial ($F_a$ = 0)."))
    w(r"\begin{table}[H]\centering\small\caption{Verificación ASME.}"
      r"\begin{tabular}{l r r r r r c}\toprule Sección & $d$ [mm] & $\alpha$ & $\tau_{máx}$ [MPa] & $S_{sd}$ [MPa] & $d_{req}$ [mm] & Estado\\\midrule")
    for s in c.secs:
        r = s.res
        w(rf"{tx(s.nombre)} & {n(s.d,1)} & {n(r['alfa'],3)} & {n(r['tau_asme'],2)} & {n(r['Ssd'],1)} & {n(r['d_asme'],1)} & {ok(r['ok_asme'])}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    s = max(c.secs, key=lambda s: s.res["tau_asme"] / s.res["Ssd"])
    r = s.res
    w(rf"""Sección más exigida, {tx(s.nombre)} ($d$ = {n(s.d,1)} mm, $M$ = {n(s.M,0)} N$\cdot$mm, $T$ = {n(abs(s.T),0)} N$\cdot$mm):
\[\tau_{{máx}} = \frac{{16}}{{\pi\,({n(s.d,1)})^3}}\sqrt{{({c.Cm:g}\times{n(s.M,0)})^2+({c.Ct:g}\times{n(abs(s.T),0)})^2}} = {n(r['tau_asme'],2)}\ \text{{MPa}} \;\le\; {n(r['Ssd'],1)}\ \text{{MPa}}\]""")
    ok_res = all(s.res["ok_asme"] for s in c.secs)
    w(r"\subsection*{Conclusión}" + (
        rf"Todas las secciones cumplen la fórmula de la ASME. La mayor utilización es {n(100*r['tau_asme']/r['Ssd'],1)} \% en {tx(s.nombre)}."
        if ok_res else rf"La sección {tx(s.nombre)} no cumple la fórmula de la ASME: requiere $d \geq$ {n(r['d_asme'],1)} mm."))

    # ---------------- 7 fatiga
    w(r"\section{Verificación por fatiga}")
    w(r"\subsection{Límite de fatiga corregido}")
    txt_tam = (r"En cada sección el límite de fatiga se multiplica además por el factor de tamaño $K_b=0.869\,d^{-0.097}$ "
               r"($d$ en pulgadas), el mismo de Soderberg (valores en la tabla de secciones críticas)." if c.tam_vm else
               r"No se aplica el factor de tamaño $K_b$ a $S_n$ (como en la fuente).")
    w(rf"""Según Bavaresco (ecs. 20 y 21): $S'_n = 0.5\,S_u = {n(c.Sn_p,1)}$ MPa y
\[S_n = C_b\,C_s\,C_r\,C_o\,S'_n = {c.Cb:g}\times{n(c.Cs,3)}\times{n(c.Cr,4)}\times{c.Co:g}\times{n(c.Sn_p,1)} = {n(c.Sn,1)}\ \text{{MPa}}\]
{txt_tam}
con $C_b$ temperatura, $C_s$ superficie (mecanizado), $C_r = 1-0.076\,B$ confiabilidad y $C_o$ esfuerzos residuales.

Para Soderberg (PDF 7-A): $S_e = \sigma_{{alt}}\,K_a K_b K_c K_d K_e K_f$, con $\sigma_{{alt}} = {n(c.sigma_alt,1)}$ MPa,
$K_a = C_s$, $K_b = 0.869\,d^{{-0.097}}$ ($d$ en in), $K_c = C_r$, $K_d = C_b$, $K_e = 1/K_f$ de la sección y
$K_f$ de efectos diversos = {c.kf_div:g}.""")
    w(r"\subsection{Von Mises (Bavaresco, ec. 19; ANSI B106.1M)}")
    w(r"""\[d = \left[\frac{10.19\,N}{1-K^4}\sqrt{\left(\frac{K_f M}{S_n}\right)^2 + 0.694\left(\frac{T}{S_y}\right)^2}\right]^{1/3}
\qquad\Rightarrow\qquad N_{real} = \frac{\pi d^3 (1-K^4)}{32\sqrt{\left(\frac{K_f M}{S_n}\right)^2 + 0.694\left(\frac{T}{S_y}\right)^2}}\]""")
    w(r"\begin{table}[H]\centering\small\caption{Fatiga por Von Mises.}"
      r"\begin{tabular}{l r r r r c}\toprule Sección & $d$ [mm] & $K_f$ & $N_{real}$ & $d_{req}$ [mm] & Estado\\\midrule")
    for s in c.secs:
        r = s.res
        w(rf"{tx(s.nombre)} & {n(s.d,1)} & {s.Kf:g} & {n(r['N_vm'],2)} & {n(r['d_vm'],1)} & {ok(r['ok_vm'])}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    w(r"\subsection{Soderberg con factores de corrección (PDF 7-A)}")
    w(r"""\[N = \frac{\pi d^3(1-K^4)}{32\sqrt{\left(\frac{T}{S_y}\right)^2+\left(\frac{M}{S_e}\right)^2}}\;\geq\;N_{mín}\]""")
    w(r"\begin{table}[H]\centering\small\caption{Fatiga por Soderberg.}"
      r"\begin{tabular}{l r r r r r r c}\toprule Sección & $d$ [mm] & $K_b$ & $K_e$ & $S_e$ [MPa] & $N$ & $d_{req}$ [mm] & Estado\\\midrule")
    for s in c.secs:
        r = s.res
        w(rf"{tx(s.nombre)} & {n(s.d,1)} & {n(r['Kb'],3)} & {n(r['Ke'],3)} & {n(r['Se'],1)} & {n(r['N_sod'],2)} & {n(r['d_sod'],1)} & {ok(r['ok_sod'])}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    sg = min(c.secs, key=lambda s: s.res["N_sod"])
    r = sg.res
    w(rf"""Sección más exigida, {tx(sg.nombre)}:
\[S_e = {n(c.sigma_alt,1)}\times{n(c.Cs,3)}\times{n(r['Kb'],3)}\times{n(c.Cr,4)}\times{c.Cb:g}\times{n(r['Ke'],3)}\times{c.kf_div:g} = {n(r['Se'],1)}\ \text{{MPa}}\]
\[N = \frac{{\pi\,({n(sg.d,1)})^3}}{{32\sqrt{{\left(\frac{{{n(abs(sg.T),0)}}}{{{n(c.Sy,1)}}}\right)^2+\left(\frac{{{n(sg.M,0)}}}{{{n(r['Se'],1)}}}\right)^2}}}} = {n(r['N_sod'],2)}\]""")
    w(r"\subsection{Diagrama S--N}")
    w(r"\begin{figure}[H]\centering" + _sn(c, sg) +
      rf"\caption{{Diagrama S--N en la sección {tx(sg.nombre)}.}}\end{{figure}}")
    w(("El esfuerzo de flexión rotativa es menor que el límite de fatiga corregido: la vida a flexión rotativa es infinita."
       if r["vida_inf"] else
       "El esfuerzo de flexión rotativa supera el límite de fatiga corregido: la vida es finita."))
    vm = min(c.secs, key=lambda s: s.res["N_vm"])
    ok_f = all(s.res["ok_vm"] and s.res["ok_sod"] for s in c.secs)
    w(r"\subsection*{Conclusión}" + (
        rf"El eje cumple a fatiga. Por Von Mises el menor factor es $N$ = {n(vm.res['N_vm'],2)} ({tx(vm.nombre)}), "
        rf"frente a {c.N_vm:g} exigido; por Soderberg es $N$ = {n(r['N_sod'],2)} ({tx(sg.nombre)}), frente a {c.N_sod:g}."
        if ok_f else
        "El eje no cumple a fatiga en las secciones marcadas REVISAR; ver los diámetros requeridos en las tablas."))

    # ---------------- 8 rigidez
    w(r"\section{Verificación por rigidez}")
    w(r"\subsection{Rigidez lateral}")
    w(rf"La flecha se obtiene del modelo de elementos finitos (método para ejes de sección variable). "
      rf"Límite: {tx(c.flecha_desc)} de luz.")
    w(r"\begin{table}[H]\centering\small\caption{Flecha máxima por luz.}"
      r"\begin{tabular}{l r r r r c}\toprule Luz & Longitud [mm] & $x$ [mm] & $y$ [mm] & $y_{perm}$ [mm] & Estado\\\midrule")
    for t in c.flechas:
        w(rf"{tx(t['tipo'])} ({n(t['a'],0)}--{n(t['b'],0)}) & {n(t['luz'],1)} & {n(t['x'],1)} & {n(t['y'],4)} & {n(t['yp'],4) if not t['info'] else '--'} & {ok(t['ok']) if not t['info'] else '--'}\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    w(r"\subsection{Pendiente}")
    if c.pend:
        w(rf"En los puntos donde se montan elementos (cargas) la pendiente no debe superar $\tan\alpha$ = {c.tan_lim:g} (CEMA, fig.~8.11).")
        w(r"\begin{table}[H]\centering\small\caption{Pendiente del eje.}\begin{tabular}{l r r c}\toprule Lugar & $x$ [mm] & $\tan\alpha$ & Estado\\\midrule")
        for p in c.pend:
            w(rf"{tx(p['lugar'])} & {n(p['x'],1)} & {n(p['tan'],6)} & {ok(p['ok'])}\\")
        for k, p in enumerate(c.pend_apoyos, 1):
            w(rf"Apoyo A{k} (informativo) & {n(p['x'],1)} & {n(p['tan'],6)} & --\\")
        w(r"\bottomrule\end{tabular}\end{table}")
        w("La pendiente en los apoyos se informa para la selección posterior de rodamientos.")
    w(r"\subsection{Rigidez torsional}")
    if c.tors:
        t = c.tors
        w(rf"""\[\theta = \frac{{180}}{{\pi}}\sum\frac{{T_i L_i}}{{G\,J_i}} = {n(t['th'],4)}^\circ\]
Límite: {tx(t['desc'])}. Longitud a torsión {n(t['L'],1)} mm, diámetro mínimo {n(t['dmin'],1)} mm:
$\theta_p$ = {n(t['thp'],4)}$^\circ$. Estado: {ok(t['ok'])}.""")
    else:
        w("El eje no transmite torque; no aplica.")
    ok_r = all(t["ok"] for t in c.flechas) and all(p["ok"] for p in c.pend) and (c.tors is None or c.tors["ok"])
    w(r"\subsection*{Conclusión}" + ("El eje cumple los límites de flecha, pendiente y ángulo de torsión."
                                     if ok_r else "El eje no cumple alguno de los límites de rigidez; ver las tablas."))

    # ---------------- 9 resumen
    # ---------------- 8b casos adicionales
    if c.casos:
        w(r"\section{Casos de carga adicionales}")
        w(r"Además del caso nominal del generador de ejes, se verifica la fluencia estática en situaciones ocasionales "
          r"(arranque del motor, sobrecarga). Los torsores, las cargas radiales y las axiales se multiplican por los "
          r"factores indicados, definidos en el archivo de datos de diseño (sección \texttt{[casos]}). Se usa el criterio de "
          r"Von Mises, $\sigma'=\sqrt{\sigma^2+3\tau^2}$, y $FS=S_y/\sigma'$, sin concentrador de esfuerzos (material dúctil).")
        w(r"\begin{table}[H]\centering\small\caption{Casos de carga adicionales.}"
          r"\begin{tabularx}{\textwidth}{X r r r r r r l c}\toprule Caso & $f_T$ & $f_r$ & $f_a$ & $T_{máx}$ [N$\cdot$m] & $M_{máx}$ [N$\cdot$m] & $FS$ & Sección & Estado\\"
          r" & & & & & & (mín. exig.) & &\\\midrule")
        for k in c.casos:
            w(rf"{tx(k['nombre'])} & {k['ft']:g} & {k['fr']:g} & {k['fa']:g} & {n(k['Tmax']/1000,1)} & {n(k['Mmax']/1000,1)} & "
              rf"{n(k['FS'],2)} ({k['fs']:g}) & {tx(k['sec'].split(' – ')[0])} & {ok(k['ok'])}\\")
        w(r"\bottomrule\end{tabularx}\end{table}")
        w(r"\subsection{Factor de seguridad por sección}")
        cab = " & ".join(rf"{tx(k['nombre'])}" for k in c.casos)
        w(r"\begin{table}[H]\centering\small\caption{Factor de seguridad a fluencia por sección y caso.}"
          r"\begin{tabular}{l r " + "r " * len(c.casos) + r"}\toprule Sección & $d$ [mm] & " + cab + r"\\\midrule")
        for i, s in enumerate(c.secs):
            fila = " & ".join(n(k["fs_secs"][i], 2) if i < len(k["fs_secs"]) else "--" for k in c.casos)
            w(rf"{tx(s.nombre)} & {n(s.d,1)} & {fila}\\")
        w(r"\bottomrule\end{tabular}\end{table}")
        w(r"\subsection{Reacciones en los apoyos por caso}")
        w(r"Las reacciones sirven para verificar los rodamientos o apoyos con la carga más desfavorable.")
        cab = " & ".join(rf"{tx(k['nombre'])} [N]" for k in c.casos)
        w(r"\begin{table}[H]\centering\small\caption{Reacciones resultantes por caso.}"
          r"\begin{tabular}{c r r " + "r " * len(c.casos) + r"}\toprule Apoyo & $x$ [mm] & Nominal [N] & " + cab + r"\\\midrule")
        for j, a in enumerate(e.apoyos):
            Rn = math.hypot(c.Ry[j], c.Rz[j])
            fila = " & ".join(n(k["R"][j], 0) for k in c.casos)
            w(rf"A{j+1} & {n(a.x,1)} & {n(Rn,0)} & {fila}\\")
        w(r"\bottomrule\end{tabular}\end{table}")

    # ---------------- 8c velocidades criticas
    vc = getattr(c, "velcr", None)
    if vc and (vc["modos"]["y"] or vc["modos"]["z"]):
        w(r"\section{Velocidades críticas}")
        w(r"La velocidad crítica lateral es la de giro a la que la frecuencia de excitación coincide con una frecuencia "
          r"natural de flexión del eje. Se obtiene resolviendo el problema de autovalores "
          r"$\mathbf{K}\boldsymbol{\phi}=\omega^2\mathbf{M}\boldsymbol{\phi}$ con el mismo modelo de elementos finitos "
          r"(apoyos incluidos) y masa concentrada en los nodos: masa propia del eje"
          + ("" if vc["incluir_eje"] else " (no incluida)") + r" más las masas puntuales declaradas. "
          r"La velocidad crítica es $n_{cr}=60\,\omega/(2\pi)$.")
        if vc["masas"]:
            w(r"\begin{table}[H]\centering\small\caption{Masas puntuales consideradas.}\begin{tabular}{l r r r}\toprule "
              r"Elemento & $x$ [mm] & $m$ [kg] & $I_p$ [kg$\cdot$m$^2$]\\\midrule")
            for mm in vc["masas"]:
                w(rf"{tx(mm['nombre'])} & {n(mm['x'],1)} & {n(mm['kg'],2)} & {n(mm['Ip'],4) if mm['Ip'] else '--'}\\")
            w(r"\bottomrule\end{tabular}\end{table}")
        else:
            w(r"\textbf{Atención:} no se declararon masas montadas en el eje (engranes, poleas, acoplamientos); "
              r"los valores son una cota superior y no deben usarse para aprobar.")
        w(r"\begin{table}[H]\centering\small\caption{Velocidades críticas laterales.}\begin{tabular}{c r r}\toprule "
          r"Modo & $n_{cr}$ plano XY [rpm] & $n_{cr}$ plano XZ [rpm]\\\midrule")
        for i in range(max(len(vc["modos"]["y"]), len(vc["modos"]["z"]))):
            a = vc["modos"]["y"][i] if i < len(vc["modos"]["y"]) else None
            b = vc["modos"]["z"][i] if i < len(vc["modos"]["z"]) else None
            w(rf"{i+1} & {n(a,0) if a else '--'} & {n(b,0) if b else '--'}\\")
        w(r"\bottomrule\end{tabular}\end{table}")
        t = vc["tors"]
        if t:
            w(rf"\textbf{{Torsional (dos inercias).}} Entre $x={t['x1']:g}$ y $x={t['x2']:g}$ mm la rigidez torsional del eje es "
              rf"$k_t={n(t['kt'],0)}$ N$\cdot$m/rad; con $I_1={t['I1']:g}$ y $I_2={t['I2']:g}$ kg$\cdot$m$^2$: "
              r"$n_{cr}=\frac{60}{2\pi}\sqrt{k_t\,(I_1+I_2)/(I_1 I_2)}="
              rf"{n(t['n'],0)}$ rpm (se desprecia la inercia del eje).")
        if vc["rpm"] > 0:
            w(rf"Velocidad de giro $n={vc['rpm']:g}$ rpm; separación mínima exigida respecto de cada crítica: {vc['margen']:g}\,\%.")
        else:
            w(r"No se indicó la velocidad de giro (\texttt{rpm} en \texttt{[velocidades]}): se informan las críticas sin criterio de aprobación.")
        w(r"No se considera el efecto giroscópico ni la inercia rotacional de las masas; el resultado es indicativo y debe "
          r"verificarse con las masas reales montadas.")

    avisos_vis = list(c.avisos) + [t for t in getattr(d, "avisos", []) if t not in c.avisos]
    if getattr(d, "por_defecto", False):
        w(r"\begin{center}\fcolorbox{rojo}{rojo!6}{\parbox{0.9\textwidth}{\centering\large\textbf{\textcolor{rojo}{DATOS POR DEFECTO -- NO VÁLIDO PARA APROBAR}}"
          r"\\[2pt]\normalsize Revise y complete el archivo de datos de diseño (.ini) y vuelva a generar la memoria.}}\end{center}")
    if avisos_vis:
        w(r"\subsection*{Avisos del cálculo}\begin{itemize}")
        for t in avisos_vis:
            w(rf"\item\relax {tx(t)}")
        w(r"\end{itemize}")
    w(r"\section{Resumen y conclusiones}")
    w(r"\begin{table}[H]\centering\small\caption{Resumen de criterios.}"
      r"\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{2.9cm} >{\raggedright\arraybackslash}p{3.6cm} >{\raggedright\arraybackslash}p{2.6cm} c}\toprule Criterio & Sección / lugar & Valor & Límite & Estado\\\midrule")
    for cr in c.criterios:
        w(rf"{tx(cr['nombre'])} & {tx(cr['sec'])} & {tx(cr['valor'])} & {tx(cr['lim'])} & {ok(cr['ok'])}\\")
    w(r"\bottomrule\end{tabularx}\end{table}")
    if c.todo_ok:
        w(r"\begin{center}\fcolorbox{verde}{verde!8}{\parbox{0.9\textwidth}{\centering\Large\textbf{\textcolor{verde}{OK}}\\[2pt]"
          r"\normalsize El eje cumple todos los criterios de resistencia, fatiga y rigidez.}}\end{center}")
    else:
        w(r"\begin{center}\fcolorbox{rojo}{rojo!6}{\parbox{0.9\textwidth}{\centering\Large\textbf{\textcolor{rojo}{REVISAR}}\\[2pt]\normalsize\raggedright")
        for cr in c.criterios:
            if not cr["ok"]:
                w(rf"\textbullet\ {tx(cr['nombre'])}: {tx(cr['accion'])}.\\")
        w(r"}}\end{center}")

    # ---------------- anexo
    w(r"\appendix\section{Supuestos y observaciones}\begin{enumerate}")
    for t in c.supuestos:
        w(rf"\item\relax {tx(t)}")
    w(r"\item El cálculo considera solo el eje: los rodamientos y soportes se seleccionan aparte.")
    for t in avisos_vis:
        w(rf"\item \textit{{Aviso:}} {tx(t)}")
    w(r"\end{enumerate}")
    w(r"\end{document}")

    with open(ruta_tex, "w", encoding="utf-8") as f:
        f.write("\n".join(S))
    return ruta_tex
