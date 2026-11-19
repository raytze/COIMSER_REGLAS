"""PASO 5 - Memoria de cálculo de la transmisión por correas en LaTeX (mismo estilo que memoria_ejes).

Cada sección es una función independiente (SECCION[nombre]); en datos_<faja>.ini
[memoria] secciones = ... o --secciones elige cuáles entran.
"""
import datetime
import math
import os

from datos import SECCIONES

_UNI = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
        ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")]
_SIM = {"τ": r"$\tau$", "θ": r"$\theta$", "α": r"$\alpha$", "β": r"$\beta$", "≥": r"$\geq$",
        "≤": r"$\leq$", "·": r"$\cdot$", "°": r"$^\circ$", "–": "--", "×": r"$\times$"}
_UNID = {"deg": r"$^\circ$", "N·m": r"N$\cdot$m", "": ""}


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


def un(u):
    return _UNID.get(u, tx(u))


def ok(b):
    return r"\textcolor{verde}{\textbf{OK}}" if b else r"\textcolor{rojo}{\textbf{REVISAR}}"


def _p(d, k):
    return d["parametros"][k] if "parametros" in d else d[k]


def _fila(d, k, simb, dec=2, desc=None):
    x = _p(d, k)
    return f"{tx(desc or x['desc'])} & ${simb}$ & {n(x['valor'], dec)} & {un(x['unidad'])}\\\\"


def _tabla(filas, titulo):
    return "\n".join([r"\begin{table}[H]\centering", rf"\caption{{{titulo}}}",
                      r"\begin{tabular}{l c r l}\toprule",
                      r"\textbf{Parámetro} & \textbf{Símbolo} & \textbf{Valor} & \textbf{Unidad}\\\midrule",
                      *filas, r"\bottomrule\end{tabular}\end{table}"])


def _ecuaciones(V, claves):
    out = [r"\begin{align*}"]
    lineas = []
    for k in claves:
        r = V["recalculo"][k]
        da = ""
        if r["da"] is not None and r["desv_pct"] is not None:
            da = rf"&&\text{{(Inventor: {n(r['da'], 3)};\ $\Delta$ = {round(r['desv_pct'], 2) + 0.0:+.2f}\,\%)}}"
        lineas.append(rf"{r['simbolo']} &= {r['formula']} = {n(r['valor'], 3)}\ \text{{{un(r['unidad'])}}} {da}")
    out.append(r"\\[3pt]".join(lineas))
    out.append(r"\end{align*}")
    return "\n".join(out)


# ------------------------------------------------------------------ secciones
def s_datos(D, V, C):
    p1, p2 = D["poleas"]
    f = [_fila(p1, "P", "P_1", 2, "Potencia de entrada"),
         _fila(p1, "Speed", "n_1", 1, "Velocidad de la polea motriz"),
         _fila(p2, "Speed", "n_2", 1, "Velocidad de la polea conducida"),
         _fila(D["calculo"], "C2", "C_2", 2), _fila(D["transmision"], "nb", "n_b", 0),
         _fila(p2, "C", "C", 1, "Distancia entre centros")]
    return r"\section{Datos de entrada}" + "\n" + _tabla(f, "Datos de la transmisión")


def s_correa(D, V, C):
    c = D["correa"]
    f = [_fila(c, k, s, dec) for k, s, dec in
         [("Lw", "L_w", 1), ("Li", "L_i", 1), ("Le", "L_e", 1), ("B", "B", 2), ("Bw", "B_w", 2),
          ("H", "H", 2), ("Alfa", r"\alpha", 1), ("SpcMass", "q", 4), ("Dwmin", r"D_{w,min}", 1)]]
    txt = (r"\section{Correa seleccionada}" "\n"
           rf"Correa trapezoidal \textbf{{{tx(c['designacion'])}}} ({tx(c['codigo'])}), "
           rf"{int(D['transmision']['nb']['valor'])} correas en paralelo.")
    return txt + "\n" + _tabla(f, "Características de la correa")


def s_geometria(D, V, C):
    p1, p2 = D["poleas"]
    t = [r"\section{Geometría de la transmisión}", r"\begin{table}[H]\centering",
         r"\caption{Poleas}", r"\begin{tabular}{l c r r l}\toprule",
         r"\textbf{Parámetro} & \textbf{Símbolo} & \textbf{Polea 1} & \textbf{Polea 2} & \textbf{Unidad}\\\midrule",
         rf"Designación & & {tx(p1['designacion'])} & {tx(p2['designacion'])} & \\"]
    for k, s, dec in [("Dw", "D_w", 1), ("Dp", "D_p", 1), ("ng", "n_g", 0), ("Sg", "e", 2),
                      ("Se", "f", 2), ("Hd", "h", 2), ("Alfa", r"\alpha_g", 1), ("Beta", r"\beta", 2),
                      ("Lf", "L_f", 1)]:
        a, b = _p(p1, k), _p(p2, k)
        t.append(rf"{tx(a['desc'])} & ${s}$ & {n(a['valor'], dec)} & {n(b['valor'], dec)} & {un(a['unidad'])}\\")
    t += [r"\bottomrule\end{tabular}\end{table}", _ecuaciones(V, ["Lw", "beta1"])]
    return "\n".join(t)


def s_cinematica(D, V, C):
    f = [_fila(D["calculo"], "s", "s", 4), _fila(D["calculo"], "fb", "f_b", 2)]
    return (r"\section{Cinemática}" "\n" + _ecuaciones(V, ["iD", "i", "v", "T1"]) + "\n"
            + _tabla(f, "Deslizamiento y frecuencia de flexión"))


def s_potencia(D, V, C):
    cal, c = D["calculo"], D["correa"]
    f = [_fila(c, "PRB", "P_{RB}", 3), _fila(cal, "C1", "C_1", 3), _fila(cal, "C2", "C_2", 2),
         _fila(c, "C3", "C_3", 3), _fila(cal, "C4", "C_4", 3), _fila(cal, "C5", "C_5", 3)]
    return (r"\section{Capacidad de potencia y número de correas}" "\n"
            + _tabla(f, "Potencia básica y factores de corrección") + "\n"
            + _ecuaciones(V, ["Pcorrea", "zer", "Cpr", "eff"]))


def s_fuerzas(D, V, C):
    p1 = D["poleas"][0]
    f = [_fila(p1, "F1", "F_1", 1), _fila(p1, "F2", "F_2", 1), _fila(D["calculo"], "k1", "k_1", 2)]
    return (r"\section{Fuerzas en la correa}" "\n" + _tabla(f, "Tensiones en los ramales") + "\n"
            + _ecuaciones(V, ["Fp", "Fe", "Fc", "Ft", "FtMax", "Fr", "Fv"]))


def s_verificacion(D, V, C):
    t = [r"\section{Verificación}", r"\begin{table}[H]\centering", r"\caption{Criterios de aceptación}",
         r"\begin{tabular}{l c r c r l c}\toprule",
         r"\textbf{Criterio} & & \textbf{Valor} & & \textbf{Límite} & & \textbf{Estado}\\\midrule"]
    for c in V["comprobaciones"]:
        op = r"$\geq$" if c["operador"] == ">=" else r"$\leq$"
        t.append(rf"{tx(c['descripcion'])} & ${c['simbolo']}$ & {n(c['valor'], 2)} & {op} & "
                 rf"{n(c['limite'], 2)} & {un(c['unidad'])} & {ok(c['cumple'])}\\")
    t += [r"\bottomrule\end{tabular}\end{table}",
          r"\textbf{Resultado:} " + ok(V["cumple"]) + " -- la transmisión "
          + ("satisface" if V["cumple"] else "no satisface") + " todos los criterios."]
    if V.get("discrepancias_con_DA"):
        t.append(r"\textcolor{rojo}{Diferencias mayores a 0.5\,\% con Inventor en: "
                 + tx(", ".join(V["discrepancias_con_DA"])) + ". ¿Falta pulsar Calcular en el generador?}")
    return "\n".join(t)


def s_cargas_eje(D, V, C):
    t = [r"\section{Cargas transmitidas a los ejes}",
         "Fuerza radial en el plano medio de cada polea, en el plano de la transmisión. "
         "Son las cargas a declarar en el generador de ejes.",
         r"\begin{table}[H]\centering", r"\caption{Cargas sobre los ejes}",
         r"\begin{tabular}{c l r r r r r}\toprule",
         r"\textbf{Polea} & \textbf{Desig.} & $T$ [N$\cdot$m] & $F_v$ [N] & $F_\perp$ [N] & "
         r"$F_r$ [N] & $\theta_c$ [$^\circ$]\\\midrule"]
    for c in C:
        t.append(rf"{c['polea']}{' (motriz)' if c['motriz'] else ''} & {tx(c['designacion'])} & "
                 rf"{n(c['T_Nm'], 2)} & {n(c['Fv_N'], 1)} & {n(c['Fperp_N'], 1)} & "
                 rf"{n(c['Fr_N'], 1)} & {n(c['angulo_linea_centros_deg'], 1)}\\")
    t += [r"\bottomrule\end{tabular}\end{table}",
          r"$\theta_c$: ángulo de la línea de centros hacia la otra polea (plano X--Y del generador). "
          r"$F_v$ va sobre esa línea y $F_\perp$ es perpendicular a ella (su signo depende del sentido de giro)."]
    return "\n".join(t)


SECCION = {s: globals()["s_" + s] for s in SECCIONES}


def generar(D, V, C, dat, ruta_tex, secciones=None):
    P = lambda k: tx(dat.s("proyecto", k))
    titulo = tx(dat.s("proyecto", "designacion") or D["nombre"])
    fecha = datetime.date.today().strftime("%d/%m/%Y")
    logo = dat.s("proyecto", "logo")
    if logo and os.path.exists(logo):
        logo_tex = rf"\includegraphics[height=2.4cm,keepaspectratio]{{{logo.replace(os.sep, '/')}}}"
    else:
        logo_tex = r"\fbox{\parbox[c][2.2cm][c]{5cm}{\centering\color{gray} LOGO}}"
    secciones = secciones or dat.secciones()
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
    w(rf"""\begin{{titlepage}}
\centering
{logo_tex}\par\vspace{{2.5cm}}
{{\Large\bfseries {P('empresa')}\par}}\vspace{{1.2cm}}
{{\Huge\bfseries\color{{azul}} MEMORIA DE CÁLCULO\par}}\vspace{{0.4cm}}
{{\LARGE\bfseries {titulo}\par}}\vspace{{0.4cm}}
{{\large Transmisión por correas trapezoidales\par}}\vspace{{2cm}}
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
    if dat.por_defecto:
        w(r"\begin{center}\fcolorbox{rojo}{white}{\parbox{0.9\linewidth}{\centering\color{rojo}\bfseries "
          r"DATOS DE PROYECTO POR DEFECTO -- NO VÁLIDO PARA APROBAR}}\end{center}")
    w(rf"""\section{{Objeto y alcance}}
Esta memoria verifica la transmisión por correas trapezoidales «{titulo}». La correa, las poleas, la
geometría, la potencia y los factores de corrección provienen del generador de correas trapezoidales
(Design Accelerator) de Autodesk Inventor. Los valores se recalculan de forma independiente y se comparan
con los de Inventor.

El alcance se limita a la transmisión. Las cargas sobre los ejes se informan para su verificación en la
memoria de cada eje.""")
    for s in SECCIONES:
        if s in secciones:
            w(SECCION[s](D, V, C))
    if dat.avisos:
        w(r"\section*{Avisos}" + "\n" + r"\begin{itemize}" + "".join(rf"\item {tx(a)}" for a in dat.avisos)
          + r"\end{itemize}")
    w(r"\end{document}")
    with open(ruta_tex, "w", encoding="utf-8") as f:
        f.write("\n".join(S) + "\n")
    return ruta_tex
