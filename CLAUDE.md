# Sistema iLogic COIMSER - Autodesk Inventor 2026

Reglas iLogic externas para ordenar obras tipo Tekla: jerarquia, marcas A0.61, planos, cut list,
plasma, reportes y revisiones, listo para Vault. Se controla Inventor con el servidor MCP `inventor`.

## Carpetas del repositorio
- `iLogic\`         reglas publicadas (iLogic apunta aqui) + TABLA_MARCAS.csv, FORMATOS_PLANCHA.csv
- `iLogic_pruebas\` reglas sin probar (no las ve iLogic). Se pasan a iLogic\ solo cuando funcionan.
- `docs\`           GUIA_USO, FICHA_RAPIDA, PRUEBAS
- `herramientas\`   ACTUALIZAR_REGLAS.bat (git pull), GUARDAR_CAMBIOS.bat (commit + push)

## Jerarquia de una obra (carpeta por fase)
```
<obra>\  <COD>-GENERAL.iam  _OBRA.txt  _MARCAS_<OBRA>.csv  REFERENCIAS\
<obra>\<COD>-<FASE>\  <COD>-<FASE>.iam  <COD>-<FASE>-<PREF>-001.iam  <conjunto>\Frame|Piezas|Referencias
                      REFERENCIAS\  PLANOS\(PLASMA, REPORTES, EMITIDOS, VIGENTES)
```
Reglas de oro: nada de conjuntos en el GENERAL; un archivo no se comparte entre fases (COPIAR_CONJUNTO);
comprar y cortar con el reporte de la FASE; nada se borra (_to_delete, _OBSOLETO, _SUPERADOS).

## Reglas para escribir reglas
1. ASCII. 2. Nada declarado (Private/Dim) antes de `Sub Main` (iLogic da error modal y bloquea Inventor).
3. VB no distingue mayusculas: una variable local con el nombre de una funcion la tapa (ej. `cortadas = Cortadas()`).
4. Asignar `HasOpenOptions`/`HasSaveCopyAsOptions` a una variable. 5. iLogic cachea: probar con copias `_t_<nombre>_<n>`.
6. Verificar el documento activo antes de correr. 7. Capas: "Oculto (ISO)" y "Hidden (ISO)".
8. Nunca sobrescribir sin respaldo; nunca borrar: mover a `_to_delete`.
9. Compilar antes de probar (ver docs/PRUEBAS.md, chequeo con vbc).
10. Dialogos modales: si Inventor no responde, buscar la ventana (win32gui) y pedir al usuario que la cierre.
11. Inventor 2026: MassProperties NO tiene PrincipalAxes/PrincipalMoments (calcular del tensor
    XYZMomentsOfInertia, cuyos productos ya son los terminos del tensor); precision =
    MassPropertiesAccuracyEnum.k_VeryHigh; filtro de planos = SelectionFilterEnum.kAllPlanarEntities.
12. Un error de compilacion abre un dialogo de iLogic al usuario: probar primero una copia con Main reducido.

## REGISTRO DE PARCHES (obligatorio)
Cada modificacion, arreglo o regla nueva instalada = una fila en docs/REGISTRO_PARCHES.csv
(FECHA;HORA;REGLA;CARPETA;VERSION_ANT;VERSION_NUEVA;TIPO;DESCRIPCION;PROBLEMA;PRUEBA;ESTADO;REINICIAR,
TIPO = NUEVA/MEJORA/CORRECCION/DATOS, sin ';' dentro de los textos), subir la version en la cabecera de la
regla, regenerar el Excel con `python herramientas/registro_parches.py <repo>` y copiar a git\docs.

## Una sola sesion de Claude controlando Inventor a la vez. Idioma: espanol.
