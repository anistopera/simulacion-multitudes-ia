# AGENTS.md — Reglas del Proyecto: Simulación de Multitudes e IA

Este repositorio implementa un prototipo 2D de simulación de multitudes con detección no supervisada de cuellos de botella (DBSCAN) y navegación adaptativa ($A^*$ y PSO).

## 1. Lectura obligatoria antes de programar
Antes de crear o modificar cualquier archivo, lee los documentos en `docs/contexto/`:
1. `docs/contexto/01_arquitectura_y_contratos.md` (firmas reales de `Entorno`, `NavegadorAdaptativo` y estructuras de datos).
2. `docs/contexto/02_formulas_y_parametros.md` (ecuaciones matemáticas exactas y umbrales).

## 2. Prohibiciones estrictas (NO HACER)
- **NO modificar** `modulos/entorno.py`, `modulos/navegacion_astar.py`, `modulos/optimizacion_pso.py` ni `configuracion.json` salvo que se pida explícitamente corregir un bug puntual.
- **NO cambiar** el sistema de coordenadas: todo el motor físico y espacial trabaja en **metros** (`float`), con origen `(0, 0)` abajo a la izquierda (`ancho = 30.0`, `alto = 20.0`).
- **NO confundir índices de matriz con `(x, y)`**: `entorno.mapa` tiene forma `(filas, columnas) = (alto, ancho) = (20, 30)`, por lo que se indexa como `mapa[fila, col] == mapa[int(y), int(x)]`.
- **NO instalar ni importar librerías externas** fuera de `requirements.txt` (solo estándar de Python + `numpy`, `scikit-learn`, `pygame`, `matplotlib`).
- **NO inventar formatos de ruta**: `NavegadorAdaptativo` escribe en `agente.ruta` una lista de waypoints `[(x, y), ...]` en metros (centros de celda). Respeta ese formato.

## 3. Convenciones de código y pruebas
- Cada nuevo módulo debe crearse dentro de `modulos/` con nombres en `snake_case`:
  - `modulos/agentes.py` (Motor de agentes y fuerzas sociales)
  - `modulos/visualizacion.py` (Renderizado en Pygame)
  - `modulos/telemetria.py` (Registro por segundo, CSV y arreglos NumPy)
  - `modulos/clustering.py` (Detección periódica con DBSCAN y métricas)
  - `modulos/diagnostico.py` (Grilla 2×2 m, estados de zona y matriz `D`)
- Todo módulo nuevo debe incluir un bloque `if __name__ == "__main__":` con una prueba autónoma ejecutable desde la raíz (`python -m modulos.<nombre>`).
- Soporta tanto instancias de clase como diccionarios cuando interactúes con `Agente` (igual que hace `_leer` y `_escribir` en `modulos/navegacion_astar.py`).

B. modulos/entorno.py -> Clase Entorno
Constructor: Entorno(ancho=30, alto=20, tam_celda=1, paso_principal=2, paso_alternativo=3, configuracion=None)

Atributos públicos: ancho (30), alto (20), tam_celda (1), filas (20), columnas (30), entrada ((1, 11)), salida ((29, 11)), destino ((29, 11)), mapa (np.ndarray uint8 de forma (20, 30), 0=libre, 1=obstáculo).

Métodos públicos:

obtener_celda(x, y) -> tuple[int, int] | None: devuelve (fila, columna) o None si está fuera.

es_transitable(x, y) -> bool: True si está dentro y mapa[fila, col] == 0.

obstaculos() -> np.ndarray: arreglo (K, 2) con [fila, columna] de celdas bloqueadas.

obtener_mapa() -> np.ndarray: copia de self.mapa.

C. modulos/navegacion_astar.py -> Clase NavegadorAdaptativo
Constructor: NavegadorAdaptativo(entorno, modo='B', alpha=2.0, tau=4.0, margen=0.10, tam_celda_D=2.0)

Métodos públicos:

asignar_ruta_inicial(agente, t=0.0, D=None) -> bool: escribe agente.ruta = [(x, y), ...].

actualizar_todos(agentes, t, D=None) -> int: actualiza rutas en modo 'B' respetando intervalo tau y mejora mínima margen.

Entrada requerida (D): np.ndarray de forma (10, 15) (celdas de 2 × 2 m sobre 20 × 30 m) con valores float en [0.0, 1.0].

D. modulos/optimizacion_pso.py
costo_J(metricas, base) -> float: espera dicts con claves 'tiempo_transito', 'tiempo_espera', 'solapamientos', 'tasa_finalizacion'.

pso(evaluar, limites=LIMITES, n_particulas=10, iteraciones=15, ...) -> tuple[mejor_theta, mejor_J, historial].

3. Módulos PENDIENTES (Contratos estrictos a respetar)
E. modulos/agentes.py (Clase Agente y gestor de simulación)
Atributos obligatorios por agente:

id: int

x: float, y: float (metros)

vx: float, vy: float (m/s)

v_deseada: float (uniforme en [0.9, 1.5] m/s)

radio: float (0.25 m)

destino: tuple[float, float] (por defecto entorno.salida)

ruta: list[tuple[float, float]] (waypoints asignados por NavegadorAdaptativo)

activo: bool (True mientras no alcance destino)

tiempo_viaje: float, tiempo_espera: float

F. modulos/telemetria.py
CSV de salida (cada 1.0 s, una fila por agente activo):t,id,x,y,vx,vy,dist_vecino_medio,t_bloqueo

Método para DBSCAN: obtener_posiciones_np() -> np.ndarray de forma (N_activos, 2) con columnas [x, y] en metros.

G. modulos/clustering.py
Ejecuta sklearn.cluster.DBSCAN(eps=1.2, min_samples=5) sobre posiciones (N, 2).

Devuelve labels (np.ndarray 1D, -1 = ruido) y resumen de clústeres (id_cluster, tamano, centroide (x, y)).

H. modulos/diagnostico.py
Divide el mapa 30 × 20 m en celdas de 2 × 2 m -> matriz de forma (10, 15) (fila_d = int(y // 2), col_d = int(x // 2)).

Devuelve:

estados: np.ndarray uint8 de forma (10, 15) (0 = Libre, 1 = Acumulación, 2 = Crítica).

D: np.ndarray float64 de forma (10, 15) con valores en [0.0, 1.0].