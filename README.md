# Reglas iLogic COIMSER

Sistema de reglas externas iLogic (Inventor 2026) para obras de estructuras metalicas:
obra -> fase -> conjunto -> pieza, marcas tipo Tekla (A0.61), planos, cut list, plasma,
pernos, cambios de material y revisiones de planos.

## Instalar en una PC
1. Instalar Git para Windows (https://git-scm.com).
2. Clonar el repositorio en una carpeta fija, por ejemplo:
   `git clone <url-del-repositorio> "D:\INGENIERIA Y CALCULO COIMSER\COIMSER_REGLAS"`
3. En Inventor: Herramientas > Opciones de iLogic > Directorios de reglas externas -> agregar
   `...\COIMSER_REGLAS\iLogic` (y quitar las carpetas viejas para no tener reglas repetidas).
4. Reiniciar Inventor. Ejecutar la regla externa **MENU_COIMSER**.

## Mantener al dia
- `herramientas\ACTUALIZAR_REGLAS.bat` -> trae la ultima version (git pull). Reiniciar Inventor.
- `herramientas\GUARDAR_CAMBIOS.bat`  -> sube un cambio con su descripcion (commit + push).
- Para volver a una version anterior: `git log --oneline` y `git checkout <codigo> -- iLogic\REGLA.iLogicVb`.

## Documentacion
- `docs\GUIA_USO.md`     guia completa para el proyectista
- `docs\FICHA_RAPIDA.md` el orden de las reglas en una pagina (para imprimir)
- `docs\PRUEBAS.md`      como probar una regla nueva antes de publicarla
