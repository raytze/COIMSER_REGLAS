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
- REORGANIZAR_OBRA: `silencioso` / `planos=NO`

## Chequeo de compilacion (antes de copiar a Inventor)
Claude compila cada regla con `vbc` simulando los tipos de Inventor: detecta errores de sintaxis,
variables no declaradas y choques de nombres (VB no distingue mayusculas). No detecta errores de la
API de Inventor: por eso siempre se prueba en la obra de prueba.
