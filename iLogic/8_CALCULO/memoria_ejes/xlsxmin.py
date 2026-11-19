"""Escritor minimo de archivos .xlsx (solo libreria estandar: zipfile).

Se usa para generar el libro de verificacion con formulas vivas sin depender de openpyxl
(la PC de trabajo solo tiene Python 3 sin librerias extra). Soporta texto, numeros, formulas,
estilos basicos, anchos de columna, paneles inmovilizados y formato condicional OK/REVISAR.
"""
import re
import zipfile
from xml.sax.saxutils import escape

# ---- estilos: nombre -> (fuente, relleno, formato numerico, alineacion, borde)
# fuentes: 0 normal, 1 negrita, 2 azul (entrada), 3 titulo, 4 nota gris cursiva, 5 blanca negrita, 6 negrita grande
_FUENTES = [
    '<font><sz val="10"/><name val="Arial"/></font>',
    '<font><b/><sz val="10"/><name val="Arial"/></font>',
    '<font><sz val="10"/><color rgb="FF0000FF"/><name val="Arial"/></font>',
    '<font><b/><sz val="14"/><name val="Arial"/></font>',
    '<font><i/><sz val="9"/><color rgb="FF595959"/><name val="Arial"/></font>',
    '<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>',
    '<font><b/><sz val="11"/><name val="Arial"/></font>',
]
# rellenos: 0 ninguno, 1 gray125 (obligatorio), 2 azul oscuro, 3 amarillo claro, 4 gris claro
_RELLENOS = [
    '<fill><patternFill patternType="none"/></fill>',
    '<fill><patternFill patternType="gray125"/></fill>',
    '<fill><patternFill patternType="solid"><fgColor rgb="FF1F3864"/><bgColor indexed="64"/></patternFill></fill>',
    '<fill><patternFill patternType="solid"><fgColor rgb="FFFFFFCC"/><bgColor indexed="64"/></patternFill></fill>',
    '<fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/><bgColor indexed="64"/></patternFill></fill>',
]
_FORMATOS = {"g": 0, "0": 1, "0.00": 2, "0.0": 164, "0.000": 165, "0.0000": 166, "#,##0": 3}
_NUMFMTS = '<numFmts count="3"><numFmt numFmtId="164" formatCode="0.0"/><numFmt numFmtId="165" formatCode="0.000"/>' \
           '<numFmt numFmtId="166" formatCode="0.0000"/></numFmts>'
_BORDES = ['<border><left/><right/><top/><bottom/><diagonal/></border>',
           '<border><left style="thin"><color rgb="FFA6A6A6"/></left><right style="thin"><color rgb="FFA6A6A6"/></right>'
           '<top style="thin"><color rgb="FFA6A6A6"/></top><bottom style="thin"><color rgb="FFA6A6A6"/></bottom><diagonal/></border>']

ESTILOS = {}   # nombre -> indice cellXfs
_XFS = []


def _def(nombre, fuente=0, relleno=0, fmt="g", alin=None, borde=0):
    ESTILOS[nombre] = len(_XFS)
    al = ""
    if alin:
        al = f'<alignment horizontal="{alin[0]}" vertical="center"' + (' wrapText="1"' if alin[1] else "") + "/>"
    _XFS.append(f'<xf numFmtId="{_FORMATOS[fmt]}" fontId="{fuente}" fillId="{relleno}" borderId="{borde}" xfId="0"'
                f' applyFont="1" applyFill="1" applyBorder="1" applyNumberFormat="1"' + (' applyAlignment="1">' + al + "</xf>" if al else "/>"))


_def("txt")
_def("negrita", 1)
_def("titulo", 3)
_def("subtitulo", 6)
_def("nota", 4, alin=("left", True))
_def("nota1", 4)
_def("enc", 5, 2, alin=("center", True), borde=1)
_def("celda", 0, 0, "g", ("left", False), 1)
_def("celdaneg", 1, 4, "g", ("left", False), 1)
for _n, _f in (("0", "0"), ("1", "0.0"), ("2", "0.00"), ("3", "0.000"), ("4", "0.0000"), ("m", "#,##0")):
    _def("in" + _n, 2, 3, _f, ("right", False), 1)     # entrada: azul sobre amarillo claro
    _def("f" + _n, 0, 0, _f, ("right", False), 1)      # formula: negro
_def("txtin", 2, 3, "g", ("left", False), 1)
_def("estado", 1, 0, "g", ("center", False), 1)


def _col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def ref(col, fila, abs_=False):
    return (f"${_col(col)}${fila}" if abs_ else f"{_col(col)}{fila}")


class Hoja:
    def __init__(self, nombre):
        self.nombre = nombre
        self.celdas = {}      # (fila, col) -> (valor, estilo)
        self.anchos = {}
        self.altos = {}
        self.cond = []        # rangos con formato OK/REVISAR
        self.congelar = None  # (fila, col) primera celda no inmovilizada
        self.combinar = []

    def set(self, fila, col, valor, estilo="txt"):
        self.celdas[(fila, col)] = (valor, estilo)

    def ancho(self, col, w):
        self.anchos[col] = w

    def _xml(self):
        filas = {}
        for (f, c), v in self.celdas.items():
            filas.setdefault(f, {})[c] = v
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
               '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>']
        out.append('<sheetViews><sheetView workbookViewId="0" showGridLines="0">')
        if self.congelar:
            f, c = self.congelar
            pa = ""
            if c > 1:
                pa += f' xSplit="{c-1}"'
            if f > 1:
                pa += f' ySplit="{f-1}"'
            out.append(f'<pane{pa} topLeftCell="{_col(c)}{f}" activePane="bottomRight" state="frozen"/>')
        out.append("</sheetView></sheetViews><sheetFormatPr defaultRowHeight=\"13.5\"/>")
        if self.anchos:
            out.append("<cols>")
            for c in sorted(self.anchos):
                out.append(f'<col min="{c}" max="{c}" width="{self.anchos[c]}" customWidth="1"/>')
            out.append("</cols>")
        out.append("<sheetData>")
        for f in sorted(filas):
            h = self.altos.get(f)
            out.append(f'<row r="{f}"' + (f' ht="{h}" customHeight="1"' if h else "") + ">")
            for c in sorted(filas[f]):
                v, est = filas[f][c]
                s = ESTILOS[est]
                r = f"{_col(c)}{f}"
                if v is None or v == "":
                    out.append(f'<c r="{r}" s="{s}"/>')
                elif isinstance(v, str) and v.startswith("="):
                    out.append(f'<c r="{r}" s="{s}"><f>{escape(v[1:])}</f></c>')
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(f'<c r="{r}" s="{s}"><v>{repr(float(v)) if isinstance(v, float) else v}</v></c>')
                else:
                    out.append(f'<c r="{r}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>')
            out.append("</row>")
        out.append("</sheetData>")
        if self.combinar:
            out.append(f'<mergeCells count="{len(self.combinar)}">' +
                       "".join(f'<mergeCell ref="{m}"/>' for m in self.combinar) + "</mergeCells>")
        pr = 1
        for rango in self.cond:
            out.append(f'<conditionalFormatting sqref="{rango}">'
                       f'<cfRule type="cellIs" dxfId="0" priority="{pr}" operator="equal"><formula>"OK"</formula></cfRule>'
                       f'<cfRule type="cellIs" dxfId="1" priority="{pr+1}" operator="equal"><formula>"REVISAR"</formula></cfRule>'
                       "</conditionalFormatting>")
            pr += 2
        out.append('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>'
                   '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/></worksheet>')
        return "".join(out)


class Libro:
    def __init__(self):
        self.hojas = []

    def hoja(self, nombre):
        h = Hoja(nombre)
        self.hojas.append(h)
        return h

    def guardar(self, ruta):
        n = len(self.hojas)
        ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
              + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                        for i in range(1, n + 1)) + "</Types>")
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
              '<bookViews><workbookView/></bookViews><sheets>'
              + "".join(f'<sheet name="{escape(h.nombre)}" sheetId="{i}" r:id="rId{i}"/>' for i, h in enumerate(self.hojas, 1))
              + '</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                            for i in range(1, n + 1))
                  + f'<Relationship Id="rId{n+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        st = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + _NUMFMTS
              + f'<fonts count="{len(_FUENTES)}">' + "".join(_FUENTES) + "</fonts>"
              + f'<fills count="{len(_RELLENOS)}">' + "".join(_RELLENOS) + "</fills>"
              + f'<borders count="{len(_BORDES)}">' + "".join(_BORDES) + "</borders>"
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              + f'<cellXfs count="{len(_XFS)}">' + "".join(_XFS) + "</cellXfs>"
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
              '<dxfs count="2">'
              '<dxf><font><b/><color rgb="FF006100"/></font><fill><patternFill><bgColor rgb="FFC6EFCE"/></patternFill></fill></dxf>'
              '<dxf><font><b/><color rgb="FF9C0006"/></font><fill><patternFill><bgColor rgb="FFFFC7CE"/></patternFill></fill></dxf>'
              "</dxfs></styleSheet>")
        with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct)
            z.writestr("_rels/.rels", rels)
            z.writestr("xl/workbook.xml", wb)
            z.writestr("xl/_rels/workbook.xml.rels", wbrels)
            z.writestr("xl/styles.xml", st)
            for i, h in enumerate(self.hojas, 1):
                z.writestr(f"xl/worksheets/sheet{i}.xml", h._xml())
