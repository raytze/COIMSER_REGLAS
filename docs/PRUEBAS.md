# Pruebas de reglas nuevas

Ninguna regla pasa de `iLogic_pruebas\` a `iLogic\` sin probarse en la **obra de prueba**
(nunca en una obra real). Todas ya compilan en el chequeo de Claude (sin errores de codigo);
falta comprobar su comportamiento en Inventor.

## Estado (2026-11-13)
| Regla | Version | Estado | Riesgo |
|---|---|---|---|
| GENERAR_PLANOS | 2.5 | sin probar (referencias ocultas en planos) | medio |
| REVISAR_JERARQUIA | 1.1 | sin probar (avisos de referencias) | bajo |
| INICIAR_CONJUNTO | 1.2 | sin probar (CREAR FASE + carpeta por fase) | bajo |
| NUEVO_PROYECTO | 1.1 | sin probar (carpeta por fase) | bajo |
| NUEVA_PIEZA / PIEZA_ASOCIADA / NUEVA_REFERENCIA | 1.1 | solo cambia la carpeta en fases nuevas | bajo |
| MENU_COIMSER | 1.0 | nueva | bajo |
| EJECUTAR_FASES | 1.0 | nueva | bajo |
| REPORTE_PERNERIA | 1.0 | nueva (solo lee y escribe Excel) | bajo |
| CAMBIOS_MATERIAL | 1.0 | nueva (solo lee y escribe Excel) | bajo |
| EMITIR_PLANOS | 1.0 | nueva: escribe propiedades en planos, PDF | medio |
| REORGANIZAR_OBRA | 1.0 | nueva: mueve archivos de fase | **alto** - copia de respaldo antes |
| COPIAR_CONJUNTO | 1.0 | nueva: copia y re-enlaza archivos | **alto** - solo en obra de prueba |
| LIMPIAR_VISTA | 1.0 | nueva - PROBADA en TST-GENERAL (archivos: 8 objetos ocultos; 3 referencias ocultas; mostrar las devuelve) | bajo |
| CAMBIAR_NATURALEZA | 1.0 | nueva - PROBADA en TST (plancha->rolada r; mecanizada->pieza; solido 8 mm -> chapa plegada con desarrollo) | bajo |
| PERFIL_A_OBRA | 1.2 | PROBADA en TST: estandar -> PF-001; personalizado suelto (piezas sueltas) -> PF-002 | bajo |
| GENERAR_PLANOS | 2.6 | desarrollo de chapa en el habilitado - PROBADO en TST (plano nuevo y plano existente) | bajo |
| EXTRAER_PIEZA | 1.0 | nueva - PROBADA en TST (plancha -> chapa 300x200, bloque -> MQ, posicion exacta) | bajo |
| AGRUPAR_EN_CONJUNTO | 1.0 | nueva - PROBADA en TST (2 piezas -> TST-ALM-BS-001, movidas, _to_delete, registro) | medio - mueve archivos |
| ESPEJO_PIEZA | 1.0 | nueva: derivada espejo + posicion reflejada | medio - probar en obra de prueba |
| TEKLA_NUMERACION | 3.8 | espejo quiral -> marca propia | bajo |
| RENOMBRAR_CONJUNTO | 1.0 | nueva: renombra archivos/carpeta, re-enlaza fase y planos | **alto** - solo en obra de prueba, nunca con check-in en Vault |

## Como probar una regla (a mano)
1. Copiar la regla de `iLogic_pruebas\` a la carpeta de reglas con un nombre temporal unico:
   `_t_EMITIR_PLANOS_1.iLogicVb` (iLogic guarda en memoria las reglas ya cargadas).
2. Reiniciar Inventor si no aparece. Abrir el documento correcto (ver tabla de abajo).
3. Ejecutarla. Si aparece "Errores de compilacion": copiar el texto y avisar (no tocar nada mas).
4. Revisar el resultado (archivos, propiedades, Excel). Si esta bien: reemplazar la regla en `iLogic\`
   (git guarda la anterior) y mover el `_t_` a `_to_delete`.

## Orden y que revisar
| # | Regla | Documento activo | Que revisar |
|---|---|---|---|
| 1 | NUEVO_PROYECTO | cualquiera | Se crea `<obra>\<COD>-<F>\<COD>-<F>.iam` con PLANOS\ y REFERENCIAS\ |
| 2 | INICIAR_CONJUNTO | el GENERAL de la prueba | CREAR FASE: carpeta, insercion fija, _OBRA.txt actualizado |
| 3 | INICIAR_CONJUNTO | la fase nueva | Subconjunto en `<fase>\<fase>-BS-001.iam` (sin carpeta duplicada) |
| 4 | NUEVA_PIEZA, PIEZA_ASOCIADA | conjunto | Piezas en `<conjunto>\Piezas\` |
| 5 | MENU_COIMSER | GENERAL, fase, plano | Opciones correctas por nivel; ejecuta y vuelve |
| 6 | TEKLA + REPORTE_PERNERIA + CAMBIOS_MATERIAL | fase numerada | Excel; correr 2 veces cambiando algo -> CAMBIOS |
| 7 | EJECUTAR_FASES | GENERAL | TODAS y una fase; RESUMEN DE OBRA |
| 8 | GENERAR_PLANOS v2.5 + EMITIR_PLANOS | fase | Rev A/0, PDF en EMITIDOS y VIGENTES, transmittal, lista; PENDIENTES tras un cambio |
| 9 | COPIAR_CONJUNTO | fase con un conjunto | Copia en la otra fase, abre sin errores, Frame Generator editable, original intacto |
| 9b | RENOMBRAR_CONJUNTO | fase con un conjunto (en TST) | Archivos y carpeta con nombre nuevo, fase y planos abren sin pedir referencias, marcas intactas, viejos en _to_delete, _RENOMBRADOS.csv; con archivos de solo lectura NO hace nada |
| 10 | REORGANIZAR_OBRA | GENERAL de una COPIA de una obra vieja | Fase movida, GENERAL abre bien, planos re-enlazados |

## Ejecucion desde Claude (servidor MCP `inventor`, execute_python)
Claude usa este codigo para correr una regla con argumentos y sin que se bloquee la conexion:
```python
import threading, pythoncom, win32com.client
ILOGIC = "{3BDD8D79-2179-4B11-8A5A-257B1C0263AC}"
def correr(regla, args=None, out={}):
    pythoncom.CoInitialize()
    try:
        app = win32com.client.Dispatch("Inventor.Application")
        auto = app.ApplicationAddIns.ItemById(ILOGIC).Automation
        nvm = app.TransientObjects.CreateNameValueMap()
        for k, v in (args or {}).items():
            nvm.Add(k, v)
        out["r"] = auto.RunExternalRuleWithArguments(app.ActiveDocument, regla, nvm)
    except Exception as e:
        out["e"] = str(e)
    finally:
        pythoncom.CoUninitialize()
res = {}
t = threading.Thread(target=correr, args=("_t_REPORTE_PERNERIA_1", {"silencioso": "1"}, res))
t.start(); t.join(120)
print("sigue corriendo (posible ventana de aviso abierta)" if t.is_alive() else res)
```
Argumentos utiles (`silencioso` evita las ventanas):
- NUEVO_PROYECTO: `nombre=PRUEBA codigo=PRU plantas=A1 raiz=<carpeta de prueba> silencioso`
- INICIAR_CONJUNTO: `fase=A2 silencioso` (en el GENERAL) / `modo=nuevo tipo=BS silencioso` (en la fase)
- EJECUTAR_FASES: `regla=REPORTE_PERNERIA fase=TODAS silencioso`
- REPORTE_PERNERIA: `reserva=5 silencioso` · CAMBIOS_MATERIAL: `silencioso` / `solo_foto`
- EMITIR_PLANOS: `planos=TODOS motivo=PARA APROBACION para=CLIENTE silencioso`
- COPIAR_CONJUNTO: seleccionar el conjunto y `fase=A2 silencioso`
- RENOMBRAR_CONJUNTO: seleccionar el conjunto y `nuevo=TST-ALM-CH-009 silencioso` (`planos=NO` para no tocar planos)
- REORGANIZAR_OBRA: `silencioso` / `planos=NO`

## Chequeo de compilacion (antes de copiar a Inventor)
Claude compila cada regla con `vbc` simulando los tipos de Inventor: detecta errores de sintaxis,
variables no declaradas y choques de nombres (VB no distingue mayusculas). No detecta errores de la
API de Inventor: por eso siempre se prueba en la obra de prueba.


## Estado al 2026-11-13 (PC coimser, obra de prueba _PRUEBAS_CHUTE\2026-001 PRUEBA CHUTE)

Todas las reglas de iLogic_pruebas estan publicadas en CLAUDE\iLogic (respaldos *.bak_1113).

PROBADAS en Inventor (con argumentos, modo silencioso):
- NUEVO_PROYECTO v1.1: obra TST con fase ALM en su carpeta (PLANOS\PLASMA, REPORTES, REFERENCIAS).
- INICIAR_CONJUNTO v1.2 modo nuevo: TST-ALM-CH-001/002.iam dentro de la carpeta de la fase.
  (OJO: usa el documento ACTIVO; CREAR FASE aun sin probar)
- NUEVA_REFERENCIA v1.2 accion=forma: <CONJ>\Referencias\<CONJ>-FRM-01.ipt, BOM Referencia.
- PIEZA_ASOCIADA v1.2 modo=caras (AFUERA y ADENTRO), congelar, descongelar:
  tolva 4 caras, PL9.5: 1 cuerpo por chapa, desarrollo OK, forma con masa 0 en el conjunto,
  ADENTRO recorta esquinas (caras 4 y 6 contra 3 y 5), cambio de ALTO 700->900 actualiza todo,
  congeladas no cambian.
- TEKLA_NUMERACION v3.7: chapas AFUERA -> n, ADENTRO -> b (cantos inclinados), forma sin marca ni peso.

Falta probar: seleccion de caras con el mouse (Pick), cuadros de dialogo, caras curvas con la regla
(probado a mano: media cana y medio cono desarrollan; cono completo NO -> partirlo), JUNTAR,
y el resto de reglas nuevas (MENU, EJECUTAR_FASES, REORGANIZAR_OBRA, PERNERIA, CAMBIOS, EMITIR, COPIAR).

- COPIAR_PIEZA v1.0 (nueva): PROBADA. Reemplazar + mantener vinculo -> PL-005 sigue a la forma;
  insertar + independiente -> PL-006 queda fija; MARCA borrada, COPIA_DE puesto, original intacta.
  Falta probar la seleccion con el mouse y los cuadros de dialogo.
- CAMBIOS_MATERIAL v1.0: PROBADA en ISLAS (ISL-1F). Foto antes / borrar una 1F-f2 / foto despues:
  MARCAS 1F-f2 8 -> 7 DISMINUYE; PLANCHAS PL1.5 271.44 -> 267.85 kg (-3.59). Perfiles sin cambio.
- LIMPIAR_OBSOLETOS v1.0 (nueva): PROBADA. TST-ALM: movio solo PL-001 (reemplazada por COPIAR_PIEZA);
  ISL-1F: movio Frame...-PZ-001/002 (copias viejas sin uso), dejo PZ-003 (en uso). Sin referencias rotas.
