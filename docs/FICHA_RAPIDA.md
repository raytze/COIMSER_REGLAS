# FICHA RAPIDA - Reglas COIMSER (imprimir y pegar junto al monitor)

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
| 8 | FASE | REVISAR_JERARQUIA | Revisar antes de numerar |
| 9 | FASE | TEKLA_NUMERACION | Marcas (EE-BS1, EE-BS1-p1) |
| 10 | FASE | TAG_EQUIPOS | TAG de fajas y equipos |
| 11 | FASE | GENERAR_PLANOS | Planos de conjuntos y piezas |
| 12 | FASE | CUT_LIST / CAMBIOS_MATERIAL / REPORTE_PERNERIA / REPORTE_ENSAMBLES | Material, cambios, pernos, pesos |
| 13 | FASE | EXPORTAR_PLASMA | DXF de corte (controla lo ya cortado) |
| 14 | FASE | EMITIR_PLANOS | Revision + PDF + transmittal + lista de planos |
| - | GENERAL | EJECUTAR_FASES | Pasos 8 a 14 en todas las fases a la vez |

**Si cambia el modelo:** 8 -> 9 -> 11 -> 12 -> 13 -> 14 (EMITIR_PLANOS -> PENDIENTES).

**Nunca:** conjuntos en el GENERAL · el mismo archivo en dos fases · borrar archivos (moverlos a `_to_delete`) ·
comprar con reportes de conjuntos sueltos (siempre el de la FASE) · mandar al taller algo que no este en `PLANOS\VIGENTES`.
