---
name: crear-modulo
description: Crea un módulo faltante de la simulación de multitudes respetando los contratos de entorno.py y navegacion_astar.py.
---
1. Lee `AGENTS.md`, `docs/contexto/01_arquitectura_y_contratos.md` y `docs/contexto/02_formulas_y_parametros.md`.
2. Verifica qué archivos ya existen en `modulos/` para no duplicar lógica ni alterar firmas existentes.
3. Implementa el módulo solicitado dentro de `modulos/` usando únicamente `numpy`, `scikit-learn`, `pygame`, `matplotlib` y la biblioteca estándar.
4. Asegura compatibilidad con objetos `Agente` y diccionarios (`getattr` / `dict.get`).
5. Añade al final del archivo un bloque `if __name__ == "__main__":` que instancie `Entorno(configuracion="configuracion.json")` y valide las formas (`shape`), tipos (`dtype`) y valores de salida.
6. Ejecuta el módulo con `python -m modulos.<nombre_modulo>` y corrige cualquier error antes de finalizar.