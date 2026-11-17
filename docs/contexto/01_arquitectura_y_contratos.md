# Arquitectura y Contratos de Interfaz Reales

## 1. Ciclo de ejecución (`main.py`)
- **Paso de física (`dt = 0.1` s):** actualización de fuerzas y posiciones de los agentes (`10` pasos por segundo simulado).
- **Paso de análisis (`1.0` s, cada 10 ticks):**
  1. `Telemetria` registra métricas y extrae posiciones `[x, y]`.
  2. `Clustering (DBSCAN)` detecta grupos espaciales sobre `[x, y]`.
  3. `Diagnostico` evalúa densidad y velocidad en celdas de `2 × 2 m` y genera la matriz `D`.
  4. `NavegadorAdaptativo` recalcula rutas con $A^*$ usando `D` (solo en `modo='B'`).

---

## 2. Módulos YA IMPLEMENTADOS (Consumir, no reescribir)

### A. `configuracion.json`
```json
{
  "ancho": 30,
  "alto": 20,
  "tam_celda": 1,
  "paso_principal": 2,
  "paso_alternativo": 3,
  "entrada": [1, 11],
  "salida": [29, 11],
  "obstaculos_extra": []
}