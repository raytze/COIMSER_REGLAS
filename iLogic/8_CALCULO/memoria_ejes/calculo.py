"""Motor de cálculo del eje (Python puro, sin numpy).

1. Viga escalonada por elementos finitos (Euler-Bernoulli) en los planos XY y XZ:
   admite cualquier número de apoyos, tramos, cargas y peso propio.
2. Esfuerzos internos por equilibrio (cortante, flector, torsor, axial).
3. Criterios por sección crítica: estático, ASME, Von Mises (Bavaresco ec. 19),
   Soderberg (PDF 7-A); rigidez lateral, pendiente y rigidez torsional.

Unidades: mm, N, N·mm, MPa.
"""
import copy
import math
from dataclasses import dataclass, field

from datos import KF_HOMBRO_REDONDEADO, KF_HOMBRO_CORTANTE, KSI_A_MPA

G_ACC = 9.80665
MM_POR_IN = 25.4
PSI_A_MPA = 0.00689476
EPS = 1e-7


# ---------------------------------------------------------------- solver banda
def _resolver_banda(K, F, bw):
    """Resuelve K u = F, K simétrica en banda (lista de filas densas). Gauss sin pivoteo."""
    n = len(F)
    A = [row[:] for row in K]
    b = F[:]
    for k in range(n):
        piv = A[k][k]
        if abs(piv) < 1e-30:
            raise ValueError("Sistema singular: el eje no está bien apoyado (se necesitan al menos 2 apoyos).")
        for i in range(k + 1, min(n, k + bw + 1)):
            if A[i][k] == 0.0:
                continue
            f = A[i][k] / piv
            for j in range(k, min(n, k + bw + 1)):
                A[i][j] -= f * A[k][j]
            b[i] -= f * b[k]
    u = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i]
        for j in range(i + 1, min(n, i + bw + 1)):
            s -= A[i][j] * u[j]
        u[i] = s / A[i][i]
    return u


def _d3_rosca(desig):
    """Diametro de nucleo (mm) de una rosca a partir de su designacion Inventor (TR14x2, M12x1.75). None si no se sabe."""
    import re
    m = re.match(r"\s*(TR|M)?\s*(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)", desig or "", re.I)
    if not m:
        return None
    pref = (m.group(1) or "").upper()
    d, P = float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", "."))
    if pref == "TR":                     # ISO 2904: d3 = d - P - 2 ac
        ac = 0.15 if P < 2 else 0.25 if P <= 5 else 0.5 if P <= 12 else 1.0
        return d - P - 2 * ac
    if pref == "M":                      # ISO 262/724: d3 = d - 1.22687 P
        return d - 1.22687 * P
    return None


# Kt a flexion de un eje escalonado con empalme (ajuste de Peterson, Shigley tabla 7-1): Kt = A (r/d)^b
_KT_FLEXION = [(1.01, 0.91938, -0.17032), (1.02, 0.96048, -0.17711), (1.03, 0.98061, -0.18381),
               (1.05, 0.98137, -0.19653), (1.07, 0.97527, -0.20958), (1.1, 0.95120, -0.23757),
               (1.2, 0.97098, -0.21796), (1.5, 0.93836, -0.25759), (2.0, 0.90879, -0.28598),
               (3.0, 0.89334, -0.30860), (6.0, 0.87868, -0.33243)]


def _kf_peterson(R, D, d, Su_mpa):
    """(Kf, Kt, q) de un hombro con empalme de radio R (mm), D>d, para flexion. q de Peterson para acero."""
    rd = R / d
    Dd = min(max(D / d, _KT_FLEXION[0][0]), _KT_FLEXION[-1][0])

    def kt(fila):
        return fila[1] * rd ** fila[2]
    for a, b in zip(_KT_FLEXION, _KT_FLEXION[1:]):
        if a[0] <= Dd <= b[0]:
            w = (Dd - a[0]) / (b[0] - a[0])
            Kt = kt(a) * (1 - w) + kt(b) * w
            break
    su = Su_mpa / 6.89476  # kpsi
    sqa = 0.246 - 3.08e-3 * su + 1.51e-5 * su ** 2 - 2.67e-8 * su ** 3  # raiz de a [raiz(in)]
    q = 1.0 / (1.0 + sqa / math.sqrt(R / 25.4))
    q = min(1.0, max(0.0, q))
    return 1.0 + q * (Kt - 1.0), Kt, q


@dataclass
class Seccion:
    nombre: str
    x: float
    d: float
    di: float
    Kf: float
    detalle: str
    concentrador: bool
    M: float = 0.0
    My: float = 0.0
    Mz: float = 0.0
    Vy: float = 0.0
    Vz: float = 0.0
    T: float = 0.0
    N: float = 0.0
    res: dict = field(default_factory=dict)


class Calculo:
    def __init__(self, eje, datos, _sub=False):
        self.eje = eje
        self.dat = datos
        self.avisos = list(eje.avisos)
        self.supuestos = []
        self._material()
        self._peso()
        self._torque()
        self._malla()
        self._resolver()
        self._diagramas()
        self._secciones()
        self._criterios()
        if _sub:
            return
        self._rigidez()
        self._resumen()
        self._casos()
        self._velocidades()
        for t in getattr(self.dat, "avisos", []):
            if t not in self.avisos:
                self.avisos.append(t)

    # ------------------------------------------------------------ material
    def _material(self):
        m = self.eje.material
        self.E, self.G = m.E, m.G
        bav = self.dat.material_bavaresco()
        if bav:
            self.mat_nombre, self.Su, self.Sy = bav[0] + " (Tabla Nº 1, Bavaresco)", bav[1], bav[2]
            if m.Sy and abs(m.Sy - self.Sy) / self.Sy > 0.02:
                self.avisos.append(
                    f"Sy del material elegido ({self.Sy:.0f} MPa) difiere del Shaft Generator ({m.Sy:.0f} MPa).")
        else:
            self.mat_nombre, self.Su, self.Sy = m.nombre, m.Su, m.Sy
        if not self.Su or not self.Sy:
            raise ValueError("El material no tiene Sy o Su. Definalos en Inventor o elija un material de Bavaresco.")
        self.rho = m.rho
        r_sy = self.Sy / self.Su
        if r_sy < 0.5 or r_sy > 0.95:
            self.avisos.append(
                f"Relación Sy/Su = {r_sy:.2f} (Sy = {self.Sy:.0f} MPa, Su = {self.Su:.0f} MPa) poco habitual en aceros: "
                "verifique el material. Si el Su real es menor, la fatiga (Sn, Se) queda sobreestimada.")
        if getattr(self.dat, "por_defecto", False):
            self.avisos.append(
                "DATOS DE DISEÑO POR DEFECTO (archivo .ini recién creado en modo silencioso: rpm, tipo de carga, "
                "confiabilidad, factores de arranque, Kf): resultado NO VÁLIDO PARA APROBAR hasta revisar el .ini.")
        self.beta = self.eje.beta if self.eje.usa_beta else 0.0
        d = self.dat
        su_ksi = self.Su / KSI_A_MPA
        self.Cs = min(0.93, max(0.68, 0.93 - (su_ksi - 40) * 0.25 / 180))
        self.B, self.Cr = d.cr()
        self.Cb = d.cb()
        self.Co = d.co()
        self.Sn_p = 0.5 * self.Su
        self.Sn = self.Cb * self.Cs * self.Cr * self.Co * self.Sn_p
        self.tam_vm = d.s("fatiga", "tamano_en_von_mises").lower() != "no"
        if self.tam_vm:
            self.supuestos.append("Von Mises (Bavaresco ec. 19): el límite de fatiga Sn se multiplica además por el factor de "
                                  "tamaño Kb de cada sección (el mismo de Soderberg). Con [fatiga] tamano_en_von_mises = no "
                                  "se usa Sn sin ese factor (como en la fuente).")
        self.sigma_alt = 0.5 * self.Su if self.Su <= 199000 * PSI_A_MPA else 99500 * PSI_A_MPA
        self.Ssd = min(0.30 * self.Sy, 0.18 * self.Su)
        self.asme_desc, self.Cm, self.Ct = d.asme()
        self.N_vm = d.f("fatiga", "N_von_mises")
        self.N_sod = d.f("fatiga", "N_min_soderberg")
        self.kf_div = d.f("fatiga", "kf_diversos")
        self.supuestos.append(
            "Factor de superficie Cs: lectura lineal de la curva «Mecanizado» del gráfico Nº 1 de Bavaresco.")

    # ------------------------------------------------------------ peso y torque
    def _peso(self):
        op = self.dat.s("operacion", "peso_propio").lower()
        self.con_peso = self.eje.usa_peso if op == "inventor" else op.startswith("s")

    def _torque(self):
        e = self.eje
        self.torques = [(c.x, c.T) for c in e.cargas if abs(c.T) > EPS]
        suma = sum(t for _, t in self.torques)
        self.x_salida = None
        if self.torques and abs(suma) > 1e-6 * max(abs(t) for _, t in self.torques):
            s = self.dat.s("operacion", "salida_torque").lower()
            L = e.longitud
            if s == "izquierda":
                xs = 0.0
            elif s == "derecha":
                xs = L
            elif s in ("", "auto"):
                # el torsor modelado es la entrada (motorreductor); sale por el elemento
                # que recibe el torque: el punto de mayor carga radial
                radiales = [c for c in e.cargas if math.hypot(c.Fy, c.Fz) > EPS and abs(c.T) <= EPS]
                if radiales:
                    mags = sorted((math.hypot(c.Fy, c.Fz) for c in radiales), reverse=True)
                    xs = max(radiales, key=lambda c: math.hypot(c.Fy, c.Fz)).x
                    if len(mags) > 1 and mags[1] >= 0.9 * mags[0]:
                        self.avisos.append(
                            "La salida del torque se eligió automáticamente entre cargas radiales de magnitud similar "
                            f"(x = {xs:.0f} mm); defina [operacion] salida_torque para evitar ambigüedad.")
                else:
                    xm = sum(x for x, _ in self.torques) / len(self.torques)
                    xs = L if xm < L / 2 else 0.0  # extremo MAS LEJANO (camino de torque mas largo: conservador)
                    self.avisos.append(
                        f"No hay cargas radiales: la salida del torque se supuso en el extremo más lejano (x = {xs:.0f} mm). "
                        "Defina [operacion] salida_torque con el punto real.")
            else:
                xs = float(s.replace(",", "."))
            self.x_salida = xs
            self.torques.append((xs, -suma))
            xe = ", ".join(f"{x:.0f}" for x, _ in self.torques[:-1])
            self.supuestos.append(
                f"En el modelo solo se define el torque de entrada (motorreductor, x = {xe} mm). "
                f"Se supone que sale por x = {xs:.0f} mm, "
                + ("el punto de mayor carga radial (elemento que recibe el torque). "
                   if s in ("", "auto") and any(abs(xs - c.x) < 1e-6 for c in e.cargas) else "según los datos de diseño. ")
                + "Solo el tramo entre ambos puntos trabaja a torsión.")

    # ------------------------------------------------------------ malla
    def _malla(self):
        e = self.eje
        L = e.longitud
        pts = {0.0, L}
        for t in e.tramos:
            pts |= {t.x0, t.x1}
        for h in e.huecos:
            pts |= {h.x0, h.x1}
        for a in e.apoyos:
            pts.add(a.x)
        for c in e.cargas:
            pts.add(c.x)
            if c.Lq > 0:
                pts.add(c.x + c.Lq)
        for o in e.operaciones:
            pts |= {o.x0, o.x1}
        for x, _ in self.torques:
            pts.add(x)
        pts = sorted(p for p in pts if -EPS <= p <= L + EPS)
        # fusionar puntos muy cercanos
        base = []
        for p in pts:
            if not base or p - base[-1] > 1e-6:
                base.append(min(max(p, 0.0), L))
        h = max(min(5.0, L / 200.0), L / 2000.0)
        xs = [base[0]]
        for a, b in zip(base, base[1:]):
            n = max(1, int(math.ceil((b - a) / h)))
            xs += [a + (b - a) * k / n for k in range(1, n + 1)]
        self.x = xs
        self.elem = []
        for a, b in zip(xs, xs[1:]):
            xm = (a + b) / 2
            D, di = e.D(xm), e.di(xm)
            I = math.pi / 64 * (D ** 4 - di ** 4)
            J = 2 * I
            A = math.pi / 4 * (D ** 2 - di ** 2)
            q = self.rho * G_ACC * A * 1e-9 if self.con_peso else 0.0
            self.elem.append(dict(a=a, b=b, D=D, di=di, I=I, J=J, A=A, qw=q))

    def _idx(self, x):
        return min(range(len(self.x)), key=lambda i: abs(self.x[i] - x))

    # ------------------------------------------------------------ FE
    def _resolver(self):
        e = self.eje
        n = len(self.x)
        ndof = 2 * n
        K = [[0.0] * ndof for _ in range(ndof)]
        Fy = [0.0] * ndof
        Fz = [0.0] * ndof
        self.dist = []  # (a, b, qy, qz) uniformes por elemento
        for k, el in enumerate(self.elem):
            Le = el["b"] - el["a"]
            EI = self.E * el["I"]
            # Timoshenko: deformación por cortante con el factor beta del Shaft Generator
            ph = 12 * EI * self.beta / (self.G * el["A"] * Le ** 2) if self.beta else 0.0
            c = EI / ((1 + ph) * Le ** 3)
            ke = [[12, 6 * Le, -12, 6 * Le], [6 * Le, (4 + ph) * Le ** 2, -6 * Le, (2 - ph) * Le ** 2],
                  [-12, -6 * Le, 12, -6 * Le], [6 * Le, (2 - ph) * Le ** 2, -6 * Le, (4 + ph) * Le ** 2]]
            dofs = [2 * k, 2 * k + 1, 2 * k + 2, 2 * k + 3]
            for i in range(4):
                for j in range(4):
                    K[dofs[i]][dofs[j]] += c * ke[i][j]
            qy, qz = el["qw"], 0.0
            xm = (el["a"] + el["b"]) / 2
            for cg in e.cargas:
                if cg.Lq > 0 and cg.x - EPS <= xm <= cg.x + cg.Lq + EPS:
                    qy += cg.qy
                    qz += cg.qz
            el["qy"], el["qz"] = qy, qz
            for F, q in ((Fy, qy), (Fz, qz)):
                if q:
                    fe = [q * Le / 2, q * Le ** 2 / 12, q * Le / 2, -q * Le ** 2 / 12]
                    for i in range(4):
                        F[dofs[i]] += fe[i]
        for cg in e.cargas:
            i = self._idx(cg.x)
            Fy[2 * i] += cg.Fy
            Fz[2 * i] += cg.Fz
            Fy[2 * i + 1] += cg.My
            Fz[2 * i + 1] += cg.Mz
        if len(e.apoyos) < 2:
            raise ValueError("El eje necesita al menos 2 apoyos radiales en el Shaft Generator.")
        self.ia = [self._idx(a.x) for a in e.apoyos]
        # Apoyos: rígidos (se restringe el desplazamiento) o elásticos (resorte k = 1/flexibilidad,
        # dato "Elasticidad" del apoyo en el generador de ejes).
        self.resorte = []
        planos = []
        self._Kplanos, self._rigidos = {}, {}
        for plano, F in (("y", Fy), ("z", Fz)):
            Kc = [row[:] for row in K]
            self._rigidos[plano] = []
            f = F[:]
            for a, i in zip(e.apoyos, self.ia):
                d = 2 * i
                cflex = a.cy if plano == "y" else a.cz
                if cflex > 1e-15:
                    Kc[d][d] += 1.0 / cflex
                else:
                    for j in range(ndof):
                        Kc[d][j] = 0.0
                        Kc[j][d] = 0.0
                    Kc[d][d] = 1.0
                    f[d] = 0.0
                    self._rigidos[plano].append(d)
            self._Kplanos[plano] = Kc
            planos.append(_resolver_banda(Kc, f, 3))
        self.uy, self.uz = planos
        self.elastico = any(a.cy > 1e-15 or a.cz > 1e-15 for a in e.apoyos)
        if self.elastico:
            self.supuestos.append("Los apoyos con elasticidad se modelan como resortes (k = 1/flexibilidad), "
                                  "igual que el generador de ejes.")
        # reacciones (fuerza del apoyo sobre el eje)
        self.Ry, self.Rz = [], []
        usados = {}
        for a, i in zip(e.apoyos, self.ia):
            d = 2 * i
            if a.cy > 1e-15:
                ry = -self.uy[d] / a.cy
            else:
                ry = sum(K[d][j] * self.uy[j] for j in range(max(0, d - 3), min(ndof, d + 4))) - Fy[d]
            if a.cz > 1e-15:
                rz = -self.uz[d] / a.cz
            else:
                rz = sum(K[d][j] * self.uz[j] for j in range(max(0, d - 3), min(ndof, d + 4))) - Fz[d]
            if i in usados:  # dos apoyos en el mismo punto
                self.avisos.append(f"Hay dos apoyos en x = {a.x:.1f} mm; la reacción se asigna al primero.")
                ry = rz = 0.0
            usados[i] = True
            self.Ry.append(ry)
            self.Rz.append(rz)
        # axial
        self.fuerzas_x = [(c.x, c.Fx) for c in e.cargas if abs(c.Fx) > EPS]
        sx = sum(f for _, f in self.fuerzas_x)
        self.x_axial = None
        if self.fuerzas_x:
            fijo = [a for a in e.apoyos if a.fijo_axial] or e.apoyos[:1]
            self.x_axial = fijo[0].x
            self.fuerzas_x.append((self.x_axial, -sx))

    # ------------------------------------------------------------ esfuerzos internos
    def _internos(self, x, lado):
        """Cortante, flector (planos y, z), torsor y axial en x; lado -1 izquierda, +1 derecha."""
        def antes(xi):
            return xi < x - EPS or (lado > 0 and abs(xi - x) <= EPS)
        Vy = Vz = My = Mz = 0.0
        for a, ry, rz in zip(self.eje.apoyos, self.Ry, self.Rz):
            if antes(a.x):
                Vy += ry; Vz += rz
                My += ry * (x - a.x); Mz += rz * (x - a.x)
        for c in self.eje.cargas:
            if antes(c.x):
                Vy += c.Fy; Vz += c.Fz
                My += c.Fy * (x - c.x); Mz += c.Fz * (x - c.x)
                My -= c.My; Mz -= c.Mz
        for el in self.elem:
            a, b = el["a"], min(el["b"], x)
            if b <= a:
                break
            l = b - a
            Vy += el["qy"] * l; Vz += el["qz"] * l
            My += el["qy"] * l * (x - (a + b) / 2)
            Mz += el["qz"] * l * (x - (a + b) / 2)
        T = sum(t for xi, t in self.torques if antes(xi))
        N = -sum(f for xi, f in self.fuerzas_x if antes(xi))
        return Vy, Vz, My, Mz, T, N

    def _diagramas(self):
        pts = []
        for i, x in enumerate(self.x):
            for lado in (-1, 1):
                Vy, Vz, My, Mz, T, N = self._internos(x, lado)
                pts.append(dict(x=x, Vy=Vy, Vz=Vz, My=My, Mz=Mz, M=math.hypot(My, Mz), T=T, N=N,
                                y=self.uy[2 * i], z=self.uz[2 * i],
                                f=math.hypot(self.uy[2 * i], self.uz[2 * i]),
                                th=math.hypot(self.uy[2 * i + 1], self.uz[2 * i + 1])))
        self.diag = pts
        self.hay_z = any(abs(c.Fz) > EPS or abs(c.qz) > EPS or abs(c.Mz) > EPS for c in self.eje.cargas)
        self.hay_axial = bool(self.fuerzas_x)
        self.hay_torque = bool(self.torques)

    # ------------------------------------------------------------ secciones críticas
    def _secciones(self):
        e = self.eje
        secs = []
        empalmes = [o for o in e.operaciones if o.tipo == "Empalme"]
        # hombros
        for t1, t2 in zip(e.tramos, e.tramos[1:]):
            if abs(t1.D2 - t2.D1) < 1e-6:
                continue
            x = t1.x1
            emp = [o for o in empalmes if abs(o.x0 - x) < 0.5]
            R = max((o.R for o in emp), default=0.0)
            d = min(t1.D2, t2.D1)
            Dmax = max(t1.D2, t2.D1)
            if R > 0 and self.dat.s("fatiga", "kf_hombro").lower() != "fijo":
                Kf, Kt, q = _kf_peterson(R, Dmax, d, self.Su)
                det = f"hombro con empalme R = {R:g} mm (r/d = {R / d:.3f}, D/d = {Dmax / d:.2f}, Kt = {Kt:.2f}, q = {q:.2f})"
                if not getattr(self, "_nota_peterson", False):
                    self._nota_peterson = True
                    self.supuestos.append("Kf de hombros con empalme: Kf = 1 + q (Kt - 1), con Kt a flexión del ajuste de Peterson "
                                          "(Shigley, tabla 7-1) en función de r/d y D/d, y q de Peterson para acero. "
                                          "Con [fatiga] kf_hombro = fijo se usan 1.5 (redondeado) y 2.5 (cortante).")
            else:
                Kf = KF_HOMBRO_REDONDEADO if R > 0 else KF_HOMBRO_CORTANTE
                det = (f"hombro con borde redondeado (R = {R:g} mm)" if R > 0 else "hombro con borde cortante")
            secs.append(Seccion(f"Hombro Ø{t1.D2:g}/Ø{t2.D1:g}", x, d, e.di(x), Kf, det, True))
        # chaveteros y ranuras
        for o in e.operaciones:
            if o.tipo == "Chavetero":
                x = self._x_max_M(o.x0, o.x1) if o.x1 > o.x0 else o.x0
                Kf = self.dat.kf_chavetero()
                secs.append(Seccion(f"Chavetero tramo {o.tramo}", x, e.D(x), e.di(x), Kf,
                                    f"chavetero de {self.dat.s('fatiga', 'chavetero')}", True))
            elif o.tipo in ("Ranura", "Rosca", "Desahogo"):
                x = (o.x0 + o.x1) / 2
                Kf, prof = self.dat.ranura(o.tipo)
                if o.prof > 0:
                    prof = o.prof  # profundidad leida de Inventor
                D = e.D(x)
                d = D - 2 * prof if 0 < prof < D / 2 - 0.5 else D
                if o.tipo == "Rosca":
                    d3 = _d3_rosca(o.desig)
                    if d3 and 0 < d3 < d:
                        d = d3
                        self.supuestos.append(f"Rosca {o.desig} del tramo {o.tramo}: se usa el diámetro de núcleo d3 = {d3:.2f} mm.")
                det = (f"{o.tipo.lower()} (Kf = {Kf:g} en el fondo"
                       + (f", Ø fondo = {d:g} mm)" if d < D else ", Ø nominal: sin reducir)"))
                if d <= e.di(x) + 0.5:
                    self.avisos.append(f"{o.tipo} del tramo {o.tramo}: el diámetro del fondo ({d:g} mm) no supera el del agujero; "
                                       "no se evalúa esa sección.")
                    continue
                secs.append(Seccion(f"{o.tipo} tramo {o.tramo}", x, d, e.di(x), Kf, det, True))
                self.supuestos.append(
                    f"{o.tipo} del tramo {o.tramo}: Kf = {Kf:g} (archivo de datos, no proviene de las fuentes)"
                    + (f"; diámetro del fondo {d:g} mm con profundidad {prof:g} mm." if d < D else
                       "; se usó el diámetro nominal porque no se definió la profundidad (resultado no conservador)."))
                if o.params:
                    self.supuestos.append(f"Parámetros de la operación leídos de Inventor ({o.clase}): " +
                                          ", ".join(f"{k} = {v:g}" for k, v in o.params.items()) + ".")
            elif o.tipo == "Agujero":
                self.supuestos.append(f"Agujero transversal en el tramo {o.tramo} ({o.clase}): no se considera su "
                                      "concentrador de esfuerzos ni la pérdida de sección; verificarlo aparte.")
        # máximo flector y máximo torsor por tramo (sección lisa)
        for t in e.tramos:
            x = self._x_max_M(t.x0, t.x1)
            secs.append(Seccion(f"Máx. flector tramo {t.idx}", x, t.D(x), e.di(x), 1.0, "sección lisa", False))
        # puntos de carga
        for c in e.cargas:
            if abs(c.Fy) + abs(c.Fz) + abs(c.T) > EPS:
                secs.append(Seccion("Punto de carga" if abs(c.T) < EPS else "Punto de torsor",
                                    c.x, e.D(c.x), e.di(c.x), 1.0, "sección lisa", False))
        # puntos con fuerza axial (incluye la reaccion en el apoyo fijo)
        for xa, _ in getattr(self, "fuerzas_x", []):
            secs.append(Seccion("Punto de carga axial", xa, e.D(xa), e.di(xa), 1.0, "sección lisa", False))
        # evaluar esfuerzos (peor lado)
        for s in secs:
            best = None
            for lado in (-1, 1):
                Vy, Vz, My, Mz, T, N = self._internos(s.x, lado)
                M = math.hypot(My, Mz)
                dd = s.d if s.d > 0 else 1.0
                f4s = max(1e-9, 1 - (s.di / dd) ** 4)
                As = math.pi / 4 * dd ** 2 * max(1e-9, 1 - (s.di / dd) ** 2)
                eq = math.sqrt((32 * M / (math.pi * dd ** 3 * f4s) + abs(N) / As) ** 2
                               + 3 * (16 * abs(T) / (math.pi * dd ** 3 * f4s)) ** 2)
                k = (round(eq, 9), M, abs(T))
                if best is None or k > best[0]:
                    best = (k, My, Mz, T, N, Vy, Vz)
            _, s.My, s.Mz, s.T, s.N, s.Vy, s.Vz = best
            s.M = math.hypot(s.My, s.Mz)
        # quitar duplicados (misma x y diámetro: queda el de mayor Kf)
        secs.sort(key=lambda s: (round(s.x, 1), -s.Kf))
        out = []
        for s in secs:
            if any(abs(o.x - s.x) < 1.0 and abs(o.d - s.d) < 1e-6 and o.Kf >= s.Kf for o in out):
                continue
            out.append(s)
        out.sort(key=lambda s: s.x)
        for i, s in enumerate(out, 1):
            s.nombre = f"S{i} – {s.nombre}"
        self.secs = out

    def _x_max_M(self, a, b):
        cand = [p for p in self.diag if a - EPS <= p["x"] <= b + EPS]
        if not cand:
            return (a + b) / 2
        p = max(cand, key=lambda p: (p["M"], abs(p["T"])))
        x = p["x"]
        return min(max(x, a), b)

    # ------------------------------------------------------------ criterios por sección
    def _kb(self, d):
        din = d / MM_POR_IN
        return 1.0 if din <= 0.3 else 0.869 * din ** (-0.097)

    def _alfa(self, s):
        """Coeficiente de columna (tabla 9.4). Tracción o sin axial: 1."""
        if s.N >= 0:
            return 1.0, None
        xs = [a.x for a in self.eje.apoyos]
        l = max(b - a for a, b in zip(xs, xs[1:]))
        K = s.di / s.d
        r = s.d / 4 * math.sqrt(1 + K ** 2)
        lr = l / r
        if lr <= 115:
            return 1 / (1 - 0.0044 * lr), lr
        n = self.dat.euler()[1]
        return self.Sy / (n * math.pi ** 2 * self.E) * lr ** 2, lr

    def _criterios(self):
        red = self.dat.s("asme", "reducir_en_hombros").lower().startswith("s")
        for s in self.secs:
            d, K = s.d, (s.di / s.d if s.d else 0.0)
            f4 = 1 - K ** 4
            M, T, Fa = s.M, abs(s.T), s.N
            A = math.pi / 4 * d ** 2 * (1 - K ** 2)
            sb = 32 * M / (math.pi * d ** 3 * f4)
            sa = Fa / A
            tau = 16 * T / (math.pi * d ** 3 * f4)
            r = s.res
            # estático (informativo)
            sig = abs(sb) + abs(sa)
            r["sb"], r["sa"], r["tau"] = sb, sa, tau
            r["svm"] = math.sqrt(sig ** 2 + 3 * tau ** 2)
            r["FS"] = self.Sy / r["svm"] if r["svm"] > 0 else float("inf")
            # ASME
            alfa, lr = self._alfa(s)
            ssd = self.Ssd * (0.75 if (s.Kf > 1 and (red or "chavetero" in s.detalle)) else 1.0)
            raiz = math.sqrt((alfa * abs(Fa) * d * (1 + K ** 2) / 8 + self.Cm * M) ** 2 + (self.Ct * T) ** 2)
            r["alfa"], r["lr"], r["Ssd"] = alfa, lr, ssd
            r["tau_asme"] = 16 / (math.pi * d ** 3 * f4) * raiz
            r["d_asme"] = (16 / (math.pi * ssd * f4) * raiz) ** (1 / 3)
            r["ok_asme"] = r["tau_asme"] <= ssd
            # Von Mises (Bavaresco ec. 19)
            Kb_vm = self._kb(d)
            Sn_s = self.Sn * (Kb_vm if self.tam_vm else 1.0)  # factor de tamano tambien en Von Mises
            r["Sn_s"] = Sn_s
            raiz_vm = math.sqrt((s.Kf * M / Sn_s) ** 2 + 0.694 * (T / self.Sy) ** 2)
            r["N_vm"] = math.pi * d ** 3 * f4 / (32 * raiz_vm) if raiz_vm > 0 else float("inf")
            r["d_vm"] = (10.19 * self.N_vm * raiz_vm / f4) ** (1 / 3)
            r["ok_vm"] = r["N_vm"] >= self.N_vm
            # Soderberg (PDF 7-A)
            Kb = self._kb(d)
            Ke = 1 / s.Kf
            Se = self.sigma_alt * self.Cs * Kb * self.Cr * self.Cb * Ke * self.kf_div
            raiz_s = math.sqrt((T / self.Sy) ** 2 + (M / Se) ** 2)
            r["Kb"], r["Ke"], r["Se"] = Kb, Ke, Se
            r["N_sod"] = math.pi * d ** 3 * f4 / (32 * raiz_s) if raiz_s > 0 else float("inf")
            r["d_sod"] = (32 * self.N_sod / (math.pi * f4) * raiz_s) ** (1 / 3)
            r["ok_sod"] = r["N_sod"] >= self.N_sod
            r["vida_inf"] = sb < Se
            r["d_req"] = max(r["d_asme"], r["d_vm"], r["d_sod"])

    # ------------------------------------------------------------ rigidez
    def _rigidez(self):
        e = self.eje
        desc, coef = self.dat.flecha()
        self.flecha_desc = desc
        ratio = coef / 12.0  # in por in de luz
        xs = [a.x for a in e.apoyos]
        L = e.longitud
        tramos = []
        bordes = [(xs[i], xs[i + 1], "Luz entre apoyos") for i in range(len(xs) - 1) if xs[i + 1] - xs[i] > 1.0]
        if xs[0] > 1.0:
            bordes.insert(0, (0.0, xs[0], "Voladizo izquierdo"))
        if L - xs[-1] > 1.0:
            bordes.append((xs[-1], L, "Voladizo derecho"))
        for a, b, tipo in bordes:
            pts = [p for p in self.diag if a - EPS <= p["x"] <= b + EPS]
            p = max(pts, key=lambda p: p["f"])
            luz = b - a
            yp = ratio * luz
            info = False
            if tipo.startswith("Voladizo"):
                cargado = any((a - EPS <= c.x <= b + EPS and math.hypot(c.Fy, c.Fz) > EPS) or
                              (math.hypot(c.qy, c.qz) > EPS and c.x < b and c.x + c.Lq > a) for c in e.cargas)
                if not cargado:
                    info = True
                    tipo += " (sin carga, informativo)"
            tramos.append(dict(tipo=tipo, a=a, b=b, luz=luz, x=p["x"], y=p["f"], yp=yp, info=info,
                               ok=info or p["f"] <= yp, fac=(p["f"] / yp) ** 0.25 if yp else 0))
        if any(t["tipo"].startswith("Voladizo") and not t["info"] for t in tramos):
            self.supuestos.append("En voladizos cargados la flecha permisible se toma con el mismo coeficiente "
                                  "sobre la longitud del voladizo (las fuentes lo dan solo entre apoyos).")
        if any(t["info"] for t in tramos):
            self.supuestos.append("Los voladizos sin carga solo giran con el eje; su flecha se informa y no se evalúa.")
        self.flechas = tramos
        # pendiente en puntos de carga (CEMA fig. 8.11) y en apoyos (informativa)
        lim = self.dat.f("rigidez", "tan_alfa_limite")
        self.tan_lim = lim
        self.pend = []
        for c in e.cargas:
            if abs(c.Fy) + abs(c.Fz) + abs(c.qy) + abs(c.qz) > EPS or abs(c.T) > EPS:
                i = self._idx(c.x)
                th = math.hypot(self.uy[2 * i + 1], self.uz[2 * i + 1])
                self.pend.append(dict(lugar="Punto de carga", x=c.x, tan=th, ok=th <= lim))
        self.pend_apoyos = []
        for a, i in zip(e.apoyos, self.ia):
            th = math.hypot(self.uy[2 * i + 1], self.uz[2 * i + 1])
            self.pend_apoyos.append(dict(x=a.x, tan=th, inv=math.tan(math.radians(a.rot_inv))))
        # torsión
        self.tors = None
        if self.hay_torque:
            desc, minpie = self.dat.torsion()
            th_rad, Ltw, dmin = 0.0, 0.0, 1e9
            bordes = sorted(x for x, _ in self.torques)
            grupos = {}
            for el in self.elem:
                xm = (el["a"] + el["b"]) / 2
                _, _, _, _, T, _ = self._internos(xm, -1)
                if abs(T) > EPS:
                    Le = el["b"] - el["a"]
                    th_rad += abs(T) * Le / (self.G * el["J"])
                    Ltw += Le
                    dmin = min(dmin, el["D"])
                    g = grupos.setdefault(sum(1 for b in bordes if b <= xm), dict(rad=0.0, L=0.0, dmin=1e9, a=el["a"], b=el["b"]))
                    g["rad"] += abs(T) * Le / (self.G * el["J"])
                    g["L"] += Le
                    g["dmin"] = min(g["dmin"], el["D"])
                    g["a"], g["b"] = min(g["a"], el["a"]), max(g["b"], el["b"])
            th = math.degrees(th_rad)
            if minpie is None:
                thp = Ltw / (20 * dmin)
            else:
                thp = minpie / 60 * (Ltw / 304.8)
            # verificacion por tramo entre torsores consecutivos (un tramo corto y muy cargado no debe esconderse)
            tramos_t = []
            for g in grupos.values():
                thg = math.degrees(g["rad"])
                thpg = g["L"] / (20 * g["dmin"]) if minpie is None else minpie / 60 * (g["L"] / 304.8)
                tramos_t.append(dict(a=g["a"], b=g["b"], L=g["L"], dmin=g["dmin"], th=thg, thp=thpg,
                                     ok=thg <= thpg, fac=(thg / thpg) ** 0.25 if thpg else 0))
            ok_t = th <= thp and all(t["ok"] for t in tramos_t)
            self.tors = dict(desc=desc, th=th, thp=thp, L=Ltw, dmin=dmin, ok=ok_t,
                             fac=(th / thp) ** 0.25 if thp else 0, tramos=tramos_t)
            if len(tramos_t) > 1:
                peor_t = max(tramos_t, key=lambda t: t["th"] / t["thp"] if t["thp"] else 0)
                if peor_t["th"] / peor_t["thp"] > th / thp:
                    self.tors.update(th=peor_t["th"], thp=peor_t["thp"], L=peor_t["L"], dmin=peor_t["dmin"], fac=peor_t["fac"],
                                     th_tot=th, thp_tot=thp)
                    self.avisos.append(f"Rigidez torsional: gobierna el tramo x = {peor_t['a']:.0f}–{peor_t['b']:.0f} mm, "
                                       "no la suma de todos los tramos a torsión.")

    # ------------------------------------------------------------ resumen
    def _resumen(self):
        cr = []
        def peor(clave, menor=True):
            vals = [(s.res[clave], s) for s in self.secs]
            return min(vals, key=lambda v: v[0]) if menor else max(vals, key=lambda v: v[0] / v[1].res["Ssd"])
        v, s = peor("N_vm")
        cr.append(dict(nombre="Fatiga – Von Mises (Bavaresco ec. 19)", valor=f"N = {v:.2f}",
                       lim=f"≥ {self.N_vm:g}", ok=v >= self.N_vm, sec=s.nombre,
                       accion=f"aumentar Ø en {s.nombre.split(' – ')[0]} a ≥ {s.res['d_vm']:.1f} mm"))
        v, s = peor("N_sod")
        cr.append(dict(nombre="Fatiga – Soderberg (PDF 7-A)", valor=f"N = {v:.2f}",
                       lim=f"≥ {self.N_sod:g}", ok=v >= self.N_sod, sec=s.nombre,
                       accion=f"aumentar Ø en {s.nombre.split(' – ')[0]} a ≥ {s.res['d_sod']:.1f} mm"))
        s = max(self.secs, key=lambda s: s.res["tau_asme"] / s.res["Ssd"])
        cr.append(dict(nombre="Resistencia – ASME (máx. esfuerzo cortante)",
                       valor=f"τ = {s.res['tau_asme']:.1f} MPa", lim=f"≤ {s.res['Ssd']:.1f} MPa",
                       ok=s.res["ok_asme"], sec=s.nombre,
                       accion=f"aumentar Ø en {s.nombre.split(' – ')[0]} a ≥ {s.res['d_asme']:.1f} mm"))
        f = max([t for t in self.flechas if not t["info"]], key=lambda t: t["y"] / t["yp"] if t["yp"] else 0)
        cr.append(dict(nombre="Rigidez lateral (flecha)", valor=f"y = {f['y']:.3f} mm",
                       lim=f"≤ {f['yp']:.3f} mm", ok=f["ok"], sec=f"{f['tipo']} ({f['a']:.0f}–{f['b']:.0f} mm)",
                       accion=f"multiplicar los Ø de esa luz por ≥ {f['fac']:.3f} o acercar los apoyos"))
        if self.pend:
            p = max(self.pend, key=lambda p: p["tan"])
            cr.append(dict(nombre="Pendiente en el punto de carga (CEMA fig. 8.11)", valor=f"tan α = {p['tan']:.5f}",
                           lim=f"≤ {self.tan_lim:g}", ok=p["ok"], sec=f"x = {p['x']:.0f} mm",
                           accion="aumentar los Ø de la luz cargada o acercar los apoyos"))
        if self.tors:
            t = self.tors
            cr.append(dict(nombre="Rigidez torsional", valor=f"θ = {t['th']:.4f}°", lim=f"≤ {t['thp']:.4f}°",
                           ok=t["ok"], sec=f"tramo a torsión, L = {t['L']:.0f} mm",
                           accion=f"multiplicar los Ø del tramo a torsión por ≥ {t['fac']:.3f}"))
        self.criterios = cr
        self.todo_ok = all(c["ok"] for c in cr)

    # ------------------------------------------------------------ casos de carga adicionales
    def _casos(self):
        """Resuelve cada caso de [casos] con las cargas escaladas y verifica la fluencia estática."""
        self.casos = []
        for k in self.dat.casos():
            e2 = copy.deepcopy(self.eje)
            for cg in e2.cargas:
                cg.Fy *= k["fr"]; cg.Fz *= k["fr"]; cg.qy *= k["fr"]; cg.qz *= k["fr"]
                cg.My *= k["fr"]; cg.Mz *= k["fr"]
                cg.Fx *= k["fa"]
                cg.T *= k["ft"]
            c2 = Calculo(e2, self.dat, _sub=True)
            s_min = min(c2.secs, key=lambda s: s.res["FS"])
            fs = s_min.res["FS"]
            R = [math.hypot(a, b) for a, b in zip(c2.Ry, c2.Rz)]
            k.update(calc=c2, FS=fs, sec=s_min.nombre, ok=fs >= k["fs"],
                     Tmax=max((abs(p["T"]) for p in c2.diag), default=0.0),
                     Mmax=max((p["M"] for p in c2.diag), default=0.0), R=R,
                     d_fac=(k["fs"] / fs) ** (1 / 3) if fs > 0 else 0.0,
                     fs_secs=[s.res["FS"] for s in c2.secs])
            self.casos.append(k)
            self.criterios.append(dict(
                nombre=f"Caso «{k['nombre']}» – fluencia estática (Von Mises)",
                valor=f"FS = {fs:.2f}", lim=f"≥ {k['fs']:g}", ok=k["ok"], sec=s_min.nombre,
                accion=f"aumentar Ø en {s_min.nombre.split(' – ')[0]} por ≥ {k['d_fac']:.3f}"))
        if self.casos:
            self.supuestos.append(
                "Casos adicionales: se verifica fluencia estática con Von Mises sin concentrador de esfuerzos "
                "(material dúctil, cargas ocasionales); las cargas se escalan con los factores de [casos] del archivo "
                "de datos. El peso propio no se escala.")
        self.todo_ok = all(c["ok"] for c in self.criterios)

    # ------------------------------------------------------------ velocidades criticas
    def _velocidades(self):
        """Velocidades criticas lateral (modelo FE con masas puntuales de [velocidades]) y torsional (2 inercias)."""
        self.velcr = None
        self.vel = self.dat.velocidades()
        try:
            import velocidades
            r = velocidades.calcular(self)
        except Exception as ex:  # no debe impedir la memoria
            self.avisos.append(f"No se pudieron calcular las velocidades críticas: {ex}")
            return
        self.velcr = r
        if not self.vel["masas"]:
            self.supuestos.append(
                "Velocidades críticas: solo se incluyó la masa del eje; los elementos montados (engranes, poleas, "
                "acoplamientos) no tienen masa en Inventor, por lo que las críticas calculadas son COTA SUPERIOR. "
                "Definirlos en [velocidades] del archivo de datos.")
        else:
            self.supuestos.append(
                "Velocidades críticas: masas puntuales de [velocidades] (sin inercia rotacional ni efecto giroscópico); "
                "frecuencia lateral con modelo de elementos finitos de masa concentrada.")
        rpm, mg = self.vel["rpm"], self.vel["margen"]
        if rpm > 0:
            import velocidades as V
            ns = [n for pl in r["modos"].values() for n in pl]
            if ns:
                s, nc = V._sep(rpm, ns, mg)
                self.criterios.append(dict(
                    nombre="Velocidad crítica lateral (separación)", valor=f"n = {rpm:g} rpm; n_cr = {nc:,.0f} rpm ({s:.0f} %)".replace(",", " "),
                    lim=f"≥ {mg:g} % de separación", ok=s >= mg, sec="Modos 1 a 3",
                    accion="modificar masas, diámetros o apoyos para alejar la resonancia, o cambiar la velocidad de operación"))
            t = r["tors"]
            if t:
                s, nc = V._sep(rpm, [t["n"]], mg)
                self.criterios.append(dict(
                    nombre="Velocidad crítica torsional (separación)", valor=f"n = {rpm:g} rpm; n_cr = {nc:,.0f} rpm ({s:.0f} %)".replace(",", " "),
                    lim=f"≥ {mg:g} % de separación", ok=s >= mg, sec=f"x = {t['x1']:g}–{t['x2']:g} mm",
                    accion="cambiar la rigidez torsional del eje o las inercias conectadas"))
            self.todo_ok = all(cr["ok"] for cr in self.criterios)
