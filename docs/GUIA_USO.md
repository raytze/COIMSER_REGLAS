# Guia de uso - Sistema iLogic COIMSER (Inventor 2026)

Para proyectistas que empiezan con el sistema. Lectura: 30 minutos. Practica: 1-2 horas con la obra de prueba.

## 1. Que es
Un conjunto de reglas iLogic que ordenan el modelo como lo hace Tekla: cada pieza y conjunto recibe una
marca unica (A0.61), y de ahi salen planos, listas de corte, DXF de plasma, pernos y reportes.
El orden de carpetas y nombres deja todo listo para Vault.

## 2. Jerarquia
```
OBRA        2026-004 MAJES\            MAJ-GENERAL.iam  (solo para ver todo)
  FASE      MAJ-ALM\MAJ-ALM.iam        plataforma / area / equipo grande (ALM, EE, CHP, ZAR...)
    CONJUNTO  MAJ-ALM-BA-001.iam       lo que se arma en taller (bastidor, viga, columna...)
      PIEZA     perfiles, planchas, chapas, mecanizadas
```
- Las **marcas** llevan la fase: `ALM-BA1` (conjunto), `ALM-BA1-p1` (pieza). El registro de marcas es uno por obra.
- Una pieza o conjunto **identico** recibe la **misma marca** (cantidad > 1).
- La **fase** es la unidad de trabajo: se numera, se dibuja, se compra, se corta y se emite por fase.

## 3. Carpetas de una obra
```
2026-004 MAJES\
   MAJ-GENERAL.iam  _OBRA.txt  _MARCAS_MAJES.csv  REFERENCIAS\ (comunes)
   MAJ-ALM\
      MAJ-ALM.iam
      MAJ-ALM-BA-001.iam      MAJ-ALM-BA-001\Frame\  Piezas\  Referencias\
      REFERENCIAS\
      PLANOS\  *.idw
               PLASMA\  (DXF, historial de corte)
               REPORTES\ (cut list, pernos, cambios, ensambles; _HISTORIAL\ con las fotos)
               EMITIDOS\<fecha>_T001\  (PDF + transmittal de cada envio)
               VIGENTES\  (ultima revision de cada plano = lo que va al taller)
```

## 4. Instalacion en una PC nueva
1. Activar el proyecto **COIMSER.ipj** en Inventor (Proyectos).
2. Clonar o copiar la carpeta de reglas (ver README) y en **Herramientas > Opciones de iLogic >
   Directorios de reglas externas** agregar `...\COIMSER_REGLAS\iLogic`.
3. Reiniciar Inventor. En el navegador de iLogic, pestana **Reglas externas**, debe verse MENU_COIMSER.
4. Ejecutar reglas: doble clic en la regla externa, o MENU_COIMSER y elegir.

## 5. Flujo de una obra paso a paso
1. **Crear la obra** - NUEVO_PROYECTO: nombre (MAJES), codigo corto (MAJ), fases (ALM, EE), cliente.
2. **Mas fases despues** - abrir el GENERAL > INICIAR_CONJUNTO > CREAR FASE NUEVA.
3. **Referencias** - en la fase: NUEVA_REFERENCIA > skeleton (ejes, niveles) o traer STEP del equipo
   (SIMPLIFICADO si solo sirve de referencia). No se numeran ni salen en planos de fabricacion.
4. **Conjuntos** - en la fase: INICIAR_CONJUNTO > CREAR SUBCONJUNTO > tipo (BS, V, C...). Entra a editarlo.
5. **Piezas** - dentro del conjunto: Frame Generator (perfiles), NUEVA_PIEZA (planchas, chapas, mecanizadas),
   PIEZA_ASOCIADA (pieza que sigue al skeleton u otra pieza; CONGELAR cuando ya esta emitida).
   Equipos comprados: INSERTAR_EQUIPO.
6. **Repetir un conjunto en otra fase** - COPIAR_CONJUNTO (nunca insertar el mismo archivo en dos fases).
   **Cambiar el nombre de un conjunto** - RENOMBRAR_CONJUNTO (antes del check-in en Vault; con check-in usar COPIAR_CONJUNTO + LIMPIAR_OBSOLETOS).
7. **Revisar** - REVISAR_JERARQUIA: piezas sueltas, conjuntos sin prefijo, referencias mal puestas.
8. **Numerar** - TEKLA_NUMERACION. Configuracion: 1 INICIAL (solo antes de emitir), 2 ANTES DE PLANOS,
   3 DESPUES DE PLANOS, 4 DESPUES DE EMITIR. Fajas / equipos: TAG_EQUIPOS.
9. **Planos** - GENERAR_PLANOS. Revisar y completar cotas a mano. TITULO_PLANO pone titulo y marcas.
10. **Material** - CUT_LIST (lista de corte y requerimiento de planchas/barras), REPORTE_PERNERIA,
    REPORTE_ENSAMBLES, y **CAMBIOS_MATERIAL** en cada emision (que cambio desde la anterior).
11. **Plasma** - EXPORTAR_PLASMA: genera el paquete del envio; lo ya cortado no se vuelve a mandar.
12. **Emitir** - EMITIR_PLANOS: revision (A, B... para aprobacion; 0, 1... para fabricacion), PDF,
    transmittal, lista de planos. Al taller solo va lo que esta en `PLANOS\VIGENTES`.
13. **Toda la obra de una vez** - desde el GENERAL: EJECUTAR_FASES (todas las fases o una) y RESUMEN DE OBRA.

## 6. Cuando cambia el diseno
REVISAR_JERARQUIA > TEKLA_NUMERACION (config. 3 o 4) > GENERAR_PLANOS > CUT_LIST + CAMBIOS_MATERIAL >
EXPORTAR_PLASMA > EMITIR_PLANOS > PENDIENTES.
- Pieza ya cortada que cambia: recibe **marca nueva** y el resumen pide avisar al taller.
- Pieza eliminada: su marca queda SIN USO; en CAMBIOS_MATERIAL aparece ELIMINADA (no se compra) y, si
  ya se corto, SOBRANTE EN TALLER.

## 7. Que hacer y que no
| Hacer | No hacer |
|---|---|
| Conjuntos dentro de una fase | Conjuntos en el GENERAL |
| COPIAR_CONJUNTO para repetir en otra fase | Insertar el mismo archivo en dos fases |
| Comprar con el reporte de la FASE | Sumar reportes de conjuntos |
| Mover a `_to_delete` | Borrar archivos |
| Guardar antes de numerar | Numerar con cambios sin guardar |
| Taller = `PLANOS\VIGENTES` | Mandar PDF sueltos o viejos |
| Reorganizar / renombrar ANTES del primer check-in en Vault | Mover carpetas despues en el Explorador |

## 8. Errores frecuentes
| Sintoma | Causa | Solucion |
|---|---|---|
| Conjunto llamado `MAJ-GENERAL-AN-001` | Se creo en el GENERAL | Borrarlo (a `_to_delete`) y crearlo dentro de la fase |
| Marca con otra fase (`AEE-...`) | PLANTA mal puesta en el ensamble padre | INICIAR_CONJUNTO > DEFINIR ESTE ENSAMBLE |
| Inventor no responde tras correr una regla | Ventana de aviso escondida detras | Alt+Tab, cerrar el aviso |
| La regla nueva no aparece | iLogic carga las reglas al iniciar | Reiniciar Inventor |
| "Abre un ensamble" | Documento activo equivocado | Activar la fase o el conjunto correcto |
| Pieza sin marca | Es comprada / Content Center / solo lectura | Correcto: va a perneria o compras |

## 9. Lectura de marcas (A0.61)
`<FASE>-<PREFIJO><n>-<codigo><n>`: EE-BS1-p3 = fase EE, bastidor 1, pieza tipo p numero 3.
Prefijos de conjunto y codigos de pieza: ver `iLogic\TABLA_MARCAS.csv`.

## 10. Practica (obra de prueba)
1. NUEVO_PROYECTO "PRUEBA", codigo PRU, fases A1.
2. En PRU-A1: INICIAR_CONJUNTO > BS. Frame Generator: 4 perfiles. NUEVA_PIEZA: plancha base.
3. Repetir con un conjunto V. COPIAR_CONJUNTO del BS a una fase A2 (crearla desde el GENERAL).
4. Desde el GENERAL: EJECUTAR_FASES > TEKLA_NUMERACION > TODAS. Luego GENERAR_PLANOS y CUT_LIST.
5. Cambiar un perfil, volver a numerar, CAMBIOS_MATERIAL, EMITIR_PLANOS > PENDIENTES.
