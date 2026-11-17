"""Genera docs/REGISTRO_PARCHES.xlsx desde docs/REGISTRO_PARCHES.csv (maestro, separado por ;)
y las versiones actuales leidas de las cabeceras de las reglas iLogic.

Uso:  python registro_parches.py <raiz_repo>
Cada parche nuevo = una fila mas en el CSV; luego se vuelve a generar el Excel.
"""
import csv, os, re, sys
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import CellIsRule, FormulaRule

raiz = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(raiz, "docs", "REGISTRO_PARCHES.csv")
out = os.path.join(raiz, "docs", "REGISTRO_PARCHES.xlsx")

F = "Arial"
H_FILL = PatternFill("solid", start_color="1F3864")
H_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
B_FONT = Font(name=F, size=10)
thin = Side(style="thin", color="BFBFBF")
BORDE = Border(left=thin, right=thin, top=thin, bottom=thin)

with open(csv_path, encoding="utf-8") as f:
    filas = list(csv.reader(f, delimiter=";"))
cab, datos = filas[0], [r for r in filas[1:] if any(c.strip() for c in r)]

wb = Workbook()

# ---------------- PARCHES ----------------
ws = wb.active
ws.title = "PARCHES"
heads = ["N", "FECHA", "HORA", "REGLA", "CARPETA", "VERSION ANTERIOR", "VERSION NUEVA", "TIPO",
         "DESCRIPCION DEL CAMBIO", "PROBLEMA QUE RESUELVE", "PRUEBA", "ESTADO", "REINICIAR INVENTOR"]
ws.append(heads)
for i, r in enumerate(datos, start=1):
    fecha = r[0].strip()
    try:
        fv = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        fv = fecha  # p.ej. "<=2026-11-16" (historial anterior al registro)
    ws.append([i, fv] + [c.strip() for c in r[1:12]])
n = len(datos) + 1
anchos = [5, 12, 7, 26, 14, 11, 11, 13, 60, 50, 26, 12, 11]
for c, w in enumerate(anchos, start=1):
    ws.column_dimensions[get_column_letter(c)].width = w
for row in ws.iter_rows(min_row=1, max_row=n):
    for cell in row:
        cell.border = BORDE
        cell.alignment = Alignment(vertical="top", wrap_text=cell.column in (9, 10, 11))
        cell.font = B_FONT
for cell in ws[1]:
    cell.fill, cell.font = H_FILL, H_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for r in range(2, n + 1):
    ws.cell(r, 2).number_format = "dd/mm/yyyy"
ws.freeze_panes = "E2"
tab = Table(displayName="Parches", ref=f"A1:{get_column_letter(len(heads))}{n}")
tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
ws.add_table(tab)
rng = f"H2:H{n}"
for txt, color in [("CORRECCION", "FCE4D6"), ("NUEVA", "E2EFDA"), ("MEJORA", "DDEBF7"), ("DATOS", "EDEDED")]:
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=[f'"{txt}"'], fill=PatternFill("solid", start_color=color)))
ws.conditional_formatting.add(f"K2:K{n}", FormulaRule(formula=['ISNUMBER(SEARCH("SIN PROBAR",K2))'], font=Font(name=F, color="C00000", bold=True)))

# ---------------- VERSIONES ----------------
wv = wb.create_sheet("VERSIONES")
wv.append(["REGLA", "CARPETA", "VERSION ACTUAL", "PARCHES REGISTRADOS", "ULTIMO PARCHE", "ULTIMA PRUEBA"])
reglas = []
il = os.path.join(raiz, "iLogic")
for dp, _, fs in os.walk(il):
    for fn in fs:
        if not fn.endswith(".iLogicVb"):
            continue
        txt = open(os.path.join(dp, fn), encoding="utf-8", errors="replace").read(3000)
        m = re.search(r"\sv(\d+\.\d+)\s", txt)
        carpeta = os.path.relpath(dp, il)
        reglas.append((fn[:-9], "(raiz)" if carpeta == "." else carpeta, ("v" + m.group(1)) if m else "-"))
reglas.sort(key=lambda x: (x[1], x[0]))
for i, (nom, carp, ver) in enumerate(reglas, start=2):
    wv.append([nom, carp, ver,
               f'=COUNTIF(PARCHES!$D:$D,A{i})',
               f'=IF(D{i}=0,"-",INDEX(PARCHES!$B:$B,_xlfn.MAXIFS(PARCHES!$A:$A,PARCHES!$D:$D,A{i})+1))',
               f'=IF(D{i}=0,"-",INDEX(PARCHES!$K:$K,_xlfn.MAXIFS(PARCHES!$A:$A,PARCHES!$D:$D,A{i})+1))'])
nv = len(reglas) + 1
for c, w in enumerate([26, 15, 14, 12, 15, 30], start=1):
    wv.column_dimensions[get_column_letter(c)].width = w
for row in wv.iter_rows(min_row=1, max_row=nv):
    for cell in row:
        cell.border, cell.font = BORDE, B_FONT
for cell in wv[1]:
    cell.fill, cell.font = H_FILL, H_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for r in range(2, nv + 1):
    wv.cell(r, 5).number_format = "dd/mm/yyyy"
    wv.cell(r, 4).alignment = Alignment(horizontal="center")
wv.freeze_panes = "A2"
tv = Table(displayName="Versiones", ref=f"A1:F{nv}")
tv.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
wv.add_table(tv)

# ---------------- LEEME ----------------
wl = wb.create_sheet("LEEME")
txt = [
    ("REGISTRO DE PARCHES - Reglas iLogic COIMSER", True),
    ("", False),
    ("PARCHES: una fila por cada modificacion, arreglo o regla nueva instalada en las reglas.", False),
    ("VERSIONES: version actual de cada regla (leida de su cabecera) y su ultimo parche (formulas).", False),
    ("", False),
    ("TIPO:  NUEVA = regla nueva   MEJORA = funcion nueva   CORRECCION = arreglo de un error   DATOS = archivos .csv/.txt", False),
    ("PRUEBA: donde se probo (TST = obra de pruebas, PLCAY = obra real en solo lectura).  SIN PROBAR en rojo = falta que el usuario la pruebe.", False),
    ("REINICIAR INVENTOR: SI = Inventor guarda las reglas en memoria; reiniciar para usar la version nueva.", False),
    ("FECHA '<=2026-11-16': cambios anteriores al inicio del registro (fecha exacta no anotada).", False),
    ("", False),
    ("El maestro es docs\\REGISTRO_PARCHES.csv (va en Git). Este Excel se regenera con herramientas\\registro_parches.py.", False),
    (f"Generado: {datetime.now():%d/%m/%Y %H:%M}", False),
]
for i, (t, b) in enumerate(txt, start=1):
    c = wl.cell(i, 1, t)
    c.font = Font(name=F, size=14 if b else 10, bold=b, color="1F3864" if b else "000000")
wl.column_dimensions["A"].width = 120

wb.move_sheet("LEEME", offset=-2)
wb.active = 1
wb.save(out)
print(out, len(datos), "parches,", len(reglas), "reglas")
