# Fórmulas Matemáticas y Parámetros Oficiales

## 1. Dinámica de Agentes (`modulos/agentes.py`)
- **Paso de tiempo:** $\Delta t = 0.1\text{ s}$, horizonte por episodio $= 180\text{ s}$.
- **Escenarios de carga:** `S1 = 40`, `S2 = 80`, `S3 = 120` agentes generados cerca de `entorno.entrada` (`[1, 11]`) con semilla `np.random.default_rng(semilla)`.
- **Fuerza resultante:**
  $$\vec{F}_i = k_o \vec{F}_{\text{objetivo}} + k_s \vec{F}_{\text{separación}} + k_r \vec{F}_{\text{obstáculos}}$$
  - Rangos de referencia: $k_o \approx 1.0$, $k_s \in [0.5, 2.0]$, $k_r \in [0.5, 3.0]$.
  - $\vec{F}_{\text{objetivo}}$ apunta al siguiente waypoint de `agente.ruta` (avanzar al siguiente waypoint al estar a $< 0.6\text{ m}$).
  - $\vec{F}_{\text{separación}}$ repele agentes cercanos ($d_{ij} < 1.2\text{ m}$).
  - $\vec{F}_{\text{obstáculos}}$ repele bordes del recinto (`0, 30, 0, 20`) y celdas ocupadas en `entorno.obstaculos()`.
- **Integración:**
  $$\vec{v}_i(t + \Delta t) = \text{clip}(\vec{v}_i(t) + \vec{F}_i \Delta t,\ \|\vec{v}\| \le v_{\text{max}})$$
  $$\vec{p}_i(t + \Delta t) = \vec{p}_i(t) + \vec{v}_i(t + \Delta t)\Delta t$$
  (Impedir que $\vec{p}_i$ entre en celdas donde `not entorno.es_transitable(x, y)`).

## 2. Telemetría (`modulos/telemetria.py`)
- **Bloqueo individual:** un agente acumula `t_bloqueo` cuando su rapidez $\|\vec{v}_i\| < 0.5 \cdot v_{\text{deseada}}$.
- **Solapamiento:** par $(i, j)$ con $i < j$ donde distancia euclidiana $d_{ij} < r_i + r_j = 0.50\text{ m}$.

## 3. DBSCAN (`modulos/clustering.py`)
- Parámetros base: `eps = 1.2` m, `min_samples = 5`, métrica euclidiana sobre `[x, y]`.
- Métricas de calidad (`silhouette_score`, `davies_bouldin_score`): calcular **solo** si hay $\ge 2$ clústeres válidos (excluyendo etiqueta `-1`).

## 4. Diagnóstico de Congestión (`modulos/diagnostico.py`)
- Cada celda $z$ mide $2 \times 2\text{ m}$ ($\text{Área} = 4.0\text{ m}^2$).
- **Densidad:** $\rho(z, t) = \frac{N(z, t)}{4.0}\ [\text{agentes/m}^2]$.
- **Reglas de clasificación:**
  - `0` (**Libre**): $\rho < 1.5$
  - `1` (**Acumulación**): $\rho \ge 1.5$ sin cumplir condición crítica
  - `2` (**Crítica**): $\rho \ge 2.0$ **y** velocidad promedio $\bar{v}(z, t) \le 0.5 \cdot \bar{v}_{\text{deseada}}$ durante al menos **3 segundos consecutivos**.
- **Matriz para $A^*$:**
  $$D(e, t) = \min\left(1.0,\ \frac{\rho(e, t)}{2.0}\right)$$