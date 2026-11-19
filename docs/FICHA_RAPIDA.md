# FICHA RAPIDA - Reglas COIMSER (imprimir y pegar junto al monitor)

## Carpetas de reglas (desde la v2 del menu)

| Carpeta | Para que | Reglas |
|---|---|---|
| (raiz) | Menu y datos | MENU_COIMSER, TABLA_MARCAS.csv, FORMATOS_PLANCHA.csv, NOTAS_FABRICACION.txt |
| 1_OBRA | Obra, fases y conjuntos | NUEVO_PROYECTO, INICIAR_CONJUNTO, AGRUPAR_EN_CONJUNTO, COPIAR_CONJUNTO, ADOPTAR_ENSAMBLE, RENOMBRAR_CONJUNTO, REORGANIZAR_OBRA |
| 2_MODELADO | Crear y cambiar piezas | NUEVA_REFERENCIA, NUEVA_PIEZA, EXTRAER_PIEZA, PIEZA_ASOCIADA, PERFIL_A_OBRA, COPIAR_PIEZA, ESPEJO_PIEZA, CAMBIAR_NATURALEZA, INSERTAR_EQUIPO |
| 3_NUMERACION | Revisar y marcar | REVISAR_JERARQUIA, REVISAR_PERFILES, TEKLA_NUMERACION, TAG_EQUIPOS |
| 4_PLANOS | Planos | GENERAR_PLANOS, TITULO_PLANO, ESTILO_PLANO, EMITIR_PLANOS |
| 5_FABRICACION | Reportes y corte | CUT_LIST, EXPORTAR_PLASMA, REPORTE_PERNERIA, REPORTE_ENSAMBLES, REPORTE_COSTO, CAMBIOS_MATERIAL |
| 6_UTILIDADES | Ayudas | EJECUTAR_FASES, TABLERO_OBRA, CAMBIOS_PIEZAS, PRUEBA_TST, LIMPIAR_VISTA, OCULTAR_SUPERFICIES, LIMPIAR_OBSOLETOS |
| 7_RELACION_POSICION | Restricciones de posicion entre piezas | PLANO_MEDIO (centrar por plano medio, tipo Width de SolidWorks) |

En iLogic solo hace falta la carpeta raiz (`...\iLogic`) en Opciones de iLogic: el menu y las reglas
buscan en las subcarpetas. MENU_COIMSER pregunta primero la ACTIVIDAD y luego la regla.


Empieza siempre con **MENU_COIMSER**: muestra solo las reglas del nivel donde estas.

| # | Donde | Regla | Para que |
|---|---|---|---|
| 1 | cualquiera | NUEVO_PROYECTO | Crear la obra: GENERAL + una carpeta por fase |
| 2 | GENERAL | INICIAR_CONJUNTO | Crear o abrir una FASE (nunca conjuntos aqui) |
| 3 | FASE | NUEVA_REFERENCIA | Skeleton, STEP de equipo, estructura existente |
| 4 | FASE | INICIAR_CONJUNTO | Crear conjunto (BS, V, C, SP...) |
| 5 | CONJUNTO | Frame Generator / NUEVA_PIEZA / PIEZA_ASOCIADA | Perfiles, planchas, piezas que siguen al skeleton |
| 6 | CONJUNTO | INSERTAR_EQUIPO | Motores, reductores, comprados |
| 7 | FASE | COPIAR_CONJUNTO | El mismo conjunto en otra fase (copia con nombres propios) |
| 7b | FASE | ADOPTAR_ENSAMBLE | Ensamble hecho FUERA de la obra: lo copia a la fase con nombres de obra, lo re-enlaza, lo define (PREFIJO/tipo) y lo inserta fijo; el externo no se toca. Despues CAMBIAR_NATURALEZA y TEKLA |
| - | CONJUNTO / FASE | ESPEJO_PIEZA | Simetria de piezas: derivada espejo con el siguiente numero en Piezas; QUIRAL=SI -> marca nueva |
| - | CONJUNTO / FASE | PLANO_MEDIO | Centrar piezas como el Width de SolidWorks: 2 caras de la pieza 1 (azul) + 2 de la pieza 2; flush/mate. Una restriccion Flush o Mate con el desfase que alinea los planos medios; no crea planos. Pieza 1 se mueve; el desfase usa los espesores actuales |
| - | CONJUNTO | EXTRAER_PIEZA | Cuerpo del STEP de referencia -> pieza real (plancha = chapa con desarrollo), misma posicion |
| - | CONJUNTO / FASE | PERFIL_A_OBRA | Perfil de Content Center en estandar -> pieza personalizada <CONJ>-PF-nnn en Piezas (mismo tamano y largo) |
| - | PIEZA / CONJUNTO | CAMBIAR_NATURALEZA | Cambia NATURALEZA, CODIGO, GRADO, ESPESOR de piezas ya creadas; convierte a chapa si hace falta |
| - | FASE | AGRUPAR_EN_CONJUNTO | Piezas sueltas seleccionadas -> conjunto nuevo <FASE>-<PREF>-nnn con sus piezas en su carpeta |
| 8 | FASE | RENOMBRAR_CONJUNTO | Cambiar el nombre de un conjunto (archivos, carpeta, referencias, planos; conserva marcas) |
| 9 | FASE | REVISAR_JERARQUIA | Revisar antes de numerar |
| 10 | FASE | TEKLA_NUMERACION | Marcas (EE-BS1, EE-BS1-p1) |
| 11 | FASE | TAG_EQUIPOS | TAG de fajas y equipos |
| 12 | FASE | GENERAR_PLANOS | Planos de conjuntos y piezas |
| 13 | FASE | CUT_LIST / CAMBIOS_MATERIAL / REPORTE_PERNERIA / REPORTE_ENSAMBLES | Material, cambios, pernos, pesos |
| 14 | FASE | EXPORTAR_PLASMA | DXF de corte (controla lo ya cortado) |
| 15 | FASE | EMITIR_PLANOS | Revision + PDF + transmittal + lista de planos |
| 16 | FASE / CONJUNTO | OCULTAR_SUPERFICIES | Apaga las superficies de referencia de PIEZA_ASOCIADA (mostrar=SI las vuelve a ver) |
| - | GENERAL / FASE / CONJUNTO | LIMPIAR_VISTA | Oculta superficies, planos, ejes, puntos y croquis de todo el ensamble (solo vista o tambien en los archivos); opcional referencias; modo 3 vuelve a mostrar |
| - | GENERAL | EJECUTAR_FASES | Pasos 8 a 14 en todas las fases a la vez. Opcion PAQUETE DE FABRICACION: ademas plano + PLASMA + REPORTES dentro de la carpeta de CADA conjunto (si REVISAR_JERARQUIA tiene errores, omite la fase) |
| - | GENERAL / FASE | TABLERO_OBRA | Excel de control: una fila por conjunto con marca, cantidad en fase, peso, ESTADO, plano y aviso |
| - | FASE / CONJUNTO | CAMBIOS_PIEZAS | Registro de cambios con fotos: nuevas, eliminadas, suprimidas, modificadas. Pregunta: VER / REGISTRAR / GUARDAR REFERENCIA |
| - | FASE | PRUEBA_TST | Prueba automatica de toda la cadena. SOLO en obras _PRUEBAS |

**Si cambia el modelo:** 8 -> 9 -> 11 -> 12 -> 13 -> 14 (EMITIR_PLANOS -> PENDIENTES).

**Nunca:** conjuntos en el GENERAL · el mismo archivo en dos fases · borrar archivos (moverlos a `_to_delete`) ·
comprar con reportes de conjuntos sueltos (siempre el de la FASE) · mandar al taller algo que no este en `PLANOS\VIGENTES`.

## Paquete por conjunto (orden constructivo)
GENERAR_PLANOS (v2.17) corrido en la FASE o en un conjunto hace el plano de ese ensamble y, en la misma corrida,
UN PLANO POR CADA CONJUNTO Y SUBCONJUNTO (a cualquier nivel) en su carpeta `<conjunto>\PLANOS\`:
- fase: disposicion general + una hoja por conjunto ("DETALLE Y HABILITADOS EN PLANO ...") + piezas sueltas;
- conjunto: su disposicion + habilitados de SUS piezas + una hoja por subconjunto con la nota al plano del subconjunto.
Si un plano viejo tenia hojas que ahora van en otro plano, se copia antes a `PLANOS\_SUPERADOS\<fecha>\` y se quitan.
`detalle=COMPLETO` = un solo plano con todo (como antes); `conjuntos=NO` = solo el plano del ensamble abierto.
Cada conjunto lleva su propia carpeta `<conjunto>\PLANOS\` con su plano (fabricacion + habilitado), `PLASMA\` y `REPORTES\`.
La fase conserva el paquete general de revision (`<fase>\PLANOS\`). Si un conjunto esta x2 en la fase (PERTENECE_A "ALM x2"),
sus piezas y DXF salen x2 y la nota del plano lo indica. El plasma no repite lo ya cortado (historial de fase + conjuntos).

## ESTADO del conjunto (solo sube)
MODELADO > NUMERADO (TEKLA) > PLANOS (GENERAR_PLANOS) > EMITIDO (EMITIR_PLANOS) > EN CORTE (EXPORTAR_PLASMA, ENVIAR AL TALLER) > FABRICADO > MONTADO.
FABRICADO y MONTADO los escribes tu en iProperties > Personalizada (ESTADO). Se ven en TABLERO_OBRA.

## Cosas a recordar
- Marca del conjunto = numero del archivo (...-CH-002 -> CH2) si esta libre. INICIAL (fase 1) solo desde la fase (PLANTA).
- EXTRAER_PIEZA reconoce cuerpos identicos del STEP (misma forma, aun girados) y coloca copias en vez de piezas nuevas.
- REVISAR_PERFILES: corrige etiquetas de perfil antes de numerar.
  Desde v1.2 corta el perfil con planos (25/50/75 %) y mide la SECCION REAL (area, inercias, alto x ancho): sirve con despuntes, ingletes y rebajes.
- Espesor de plancha: plasma y cut list usan el espesor MEDIDO de la pieza. Si cambias el espesor, cambia el parametro ESPESOR (no escribas el numero en la extrusion); REVISAR_JERARQUIA marca ERROR si no coinciden.
- Pieza hecha antes / de otra obra / suelta: seleccionala y corre COPIAR_PIEZA -> TRAER A LA OBRA (copia en la carpeta del conjunto, el original no se toca).
- Subconjuntos dentro de subconjuntos: abre (o edita en el sitio) el conjunto y AGRUPAR_EN_CONJUNTO ahi. Recomendado maximo 3 niveles: la ruta de los archivos no puede pasar de 259 caracteres (la regla se detiene en 250).
- Planos de rotulo: etiquetas SECCION A-A / DETALLE B normales y logo vectorial (sale en DWG/DXF) con ESTILO_PLANO v1.2.
- Para correr GENERAR_PLANOS en un conjunto, el conjunto debe estar abierto y activo (EJECUTAR_FASES lo hace solo).

## Registro de cambios (CAMBIOS_PIEZAS)
1. Despues de emitir planos: CAMBIOS_PIEZAS > GUARDAR REFERENCIA (guarda datos y fotos de cada pieza y conjunto en `<conjunto>\PLANOS\_FOTOS`).
2. Despues de modificar: CAMBIOS_PIEZAS > REGISTRAR CAMBIOS. Escribe el motivo; genera `REPORTES_OBRA\<COD>-REGISTRO_CAMBIOS.xlsx` con una fila por cambio y fotos antes / ahora (el historico esta en REGISTRO_CAMBIOS.csv y `_FOTOS_CAMBIOS`).
3. Tras reemitir los planos de los conjuntos indicados: GUARDAR REFERENCIA otra vez (o REGISTRAR Y GUARDAR).
Sin referencia previa no hay con que comparar. Las fotos tardan 1-3 s por pieza (arg fotos=NO las omite).

## Deshacer (RESPALDOS)
REVISAR_PERFILES, TEKLA_NUMERACION y CAMBIAR_NATURALEZA copian cada archivo ANTES de guardarlo en
`CLAUDE\_RESPALDOS\<obra>\<fecha_hora>_<REGLA>\` (fuera de la obra y de Vault). Para volver atras:
cierra el ensamble y corre RESTAURAR_RESPALDO (menu 6), elige la tanda y confirma. La version que
reemplazas tambien queda respaldada (ANTES_DE_RESTAURAR). Otra carpeta: escribela en `iLogic\RESPALDOS.txt`.
