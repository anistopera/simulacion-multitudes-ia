# -*- coding: utf-8 -*-
"""
Módulo 6: Diagnóstico de congestión
Responsable: Lora Quilla Santiago Leonardo

Qué hace este módulo
--------------------
Decide qué zonas del escenario de simulación están realmente congestionadas,
aplicando el principio: "juntarse no es lo mismo que estar atascado".

El módulo discretiza el recinto (30 x 20 m) en una cuadrícula de celdas de 2 x 2 m
(10 filas x 15 columnas). Para cada celda calcula:
  1. Densidad local: agentes / área útil (agentes/m²).
  2. Velocidad media local: promedio del módulo de velocidades (m/s).
  3. Persistencia temporal: tiempo acumulado con densidad crítica y baja velocidad.

Clasificación de estados por reglas
-----------------------------------
- LIBRE:       densidad < 1.5 agentes/m²
- ACUMULACIÓN: densidad >= 1.5 agentes/m² sin bloqueo prolongado
- CRÍTICA:     densidad >= 2.0 agentes/m² Y velocidad <= 50 % de la deseada
               durante al menos 3.0 segundos continuos.

Matriz de costo para A*
-----------------------
Genera la matriz D(e, t) = mín(1.0; densidad / 2.0), con forma (10, 15) y valores
en [0.0, 1.0], la cual es consumida directamente por el Módulo 7 (Navegación A*).
"""

import math
from pathlib import Path
import numpy as np

# Constantes de configuración según acuerdos de interfaz del proyecto
TAM_CELDA_DEFECTO = 2.0          # Tamaño de celda en metros (2x2 m)
ANCHO_ESCENARIO = 30.0          # Ancho del recinto en metros
ALTO_ESCENARIO = 20.0           # Alto del recinto en metros

# Umbrales operativos acordados
UMBRAL_DENSIDAD_ALERTA = 1.5    # agentes/m²
UMBRAL_DENSIDAD_CRITICA = 2.0   # agentes/m²
FACTOR_VELOCIDAD_CRITICA = 0.50 # 50% de la velocidad deseada
PERSISTENCIA_MINIMA = 3.0       # Segundos mínimos para confirmar estado crítico
V_DESEADA_NOMINAL = 1.2         # m/s (valor de referencia si el agente no lo indica)

# Estados de diagnóstico
ESTADO_LIBRE = "libre"
ESTADO_ACUMULACION = "acumulacion"
ESTADO_CRITICA = "critica"
ESTADO_OBSTACULO = "obstaculo"

# Códigos numéricos para operaciones matriciales rápidas y visualización
CODIGO_ESTADO = {
    ESTADO_LIBRE: 0,
    ESTADO_ACUMULACION: 1,
    ESTADO_CRITICA: 2,
    ESTADO_OBSTACULO: -1
}


class DiagnosticoCongestion:
    """
    Gestiona la discretización espacial en celdas de 2x2 m, evalúa densidades,
    velocidades y persistencia temporal, y emite la clasificación de zonas
    junto con la matriz de costos D(e, t) para A*.
    """

    def __init__(self, entorno=None, ancho=ANCHO_ESCENARIO, alto=ALTO_ESCENARIO,
                 tam_celda=TAM_CELDA_DEFECTO, umbral_alerta=UMBRAL_DENSIDAD_ALERTA,
                 umbral_critica=UMBRAL_DENSIDAD_CRITICA, factor_v_critica=FACTOR_VELOCIDAD_CRITICA,
                 persistencia_min=PERSISTENCIA_MINIMA):
        """
        Inicializa la cuadrícula de diagnóstico.

        Parámetros:
            entorno: Instancia opcional de la clase Entorno (para calcular área útil exacta).
            ancho, alto: Dimensiones del recinto en metros (30 x 20 m).
            tam_celda: Tamaño de celda en metros (2.0 m).
            umbral_alerta: Densidad para estado de acumulación (1.5 agentes/m²).
            umbral_critica: Densidad para condición crítica (2.0 agentes/m²).
            factor_v_critica: Fracción de v_deseada para considerar bloqueo (0.50).
            persistencia_min: Tiempo en segundos para confirmar congestión crítica (3.0 s).
        """
        if entorno is not None:
            self.ancho = float(getattr(entorno, 'ancho', ancho))
            self.alto = float(getattr(entorno, 'alto', alto))
        else:
            self.ancho = float(ancho)
            self.alto = float(alto)

        self.tam_celda = float(tam_celda)
        self.filas = int(math.ceil(self.alto / self.tam_celda))       # 20 / 2 = 10
        self.columnas = int(math.ceil(self.ancho / self.tam_celda))   # 30 / 2 = 15
        self.forma = (self.filas, self.columnas)

        self.umbral_alerta = float(umbral_alerta)
        self.umbral_critica = float(umbral_critica)
        self.factor_v_critica = float(factor_v_critica)
        self.persistencia_min = float(persistencia_min)

        # Cálculo del área útil por celda considerando obstáculos del entorno
        self.area_util = self._calcular_area_util(entorno)

        # Matrices de estado y monitoreo temporal
        self.densidad = np.zeros(self.forma, dtype=float)
        self.velocidad_promedio = np.zeros(self.forma, dtype=float)
        self.conteo_agentes = np.zeros(self.forma, dtype=int)
        self.tiempo_bloqueo = np.zeros(self.forma, dtype=float)
        self.estados = np.full(self.forma, ESTADO_LIBRE, dtype=object)
        self.estados_codigo = np.zeros(self.forma, dtype=int)
        self.matriz_D = np.zeros(self.forma, dtype=float)

        # Si una celda es 100% obstáculo, se marca desde el inicio
        for f in range(self.filas):
            for c in range(self.columnas):
                if self.area_util[f, c] <= 0.0:
                    self.estados[f, c] = ESTADO_OBSTACULO
                    self.estados_codigo[f, c] = CODIGO_ESTADO[ESTADO_OBSTACULO]

    def _calcular_area_util(self, entorno):
        """
        Calcula el área transitable (en m²) dentro de cada celda de 2x2 m.
        Si se dispone de la cuadrícula de obstáculos de 1x1 m del Entorno,
        descuenta las subceldas bloqueadas.
        """
        area_nominal = self.tam_celda * self.tam_celda  # 2.0 * 2.0 = 4.0 m²
        area = np.full(self.forma, area_nominal, dtype=float)

        if entorno is None or not hasattr(entorno, 'mapa'):
            return area

        tam_e = float(getattr(entorno, 'tam_celda', 1.0))
        mapa_e = entorno.mapa  # mapa de 1s (obstáculo) y 0s (libre)

        for f in range(self.filas):
            y_min = f * self.tam_celda
            y_max = min(self.alto, (f + 1) * self.tam_celda)
            for c in range(self.columnas):
                x_min = c * self.tam_celda
                x_max = min(self.ancho, (c + 1) * self.tam_celda)

                # Mapear a índices de celdas de 1x1 m del entorno
                f_e_min = int(y_min / tam_e)
                f_e_max = int(math.ceil(y_max / tam_e))
                c_e_min = int(x_min / tam_e)
                c_e_max = int(math.ceil(x_max / tam_e))

                submapa = mapa_e[f_e_min:f_e_max, c_e_min:c_e_max]
                num_obstaculos = np.sum(submapa == 1)
                area_bloqueada = float(num_obstaculos) * (tam_e * tam_e)
                area[f, c] = max(0.0, area_nominal - area_bloqueada)

        return area

    def obtener_celda(self, x, y):
        """
        Convierte coordenadas continuas (x, y) en metros a índices (fila, columna)
        en la cuadrícula de 2x2 m. Devuelve None si está fuera de límites.
        """
        if not (0.0 <= x < self.ancho and 0.0 <= y < self.alto):
            return None
        fila = int(y / self.tam_celda)
        columna = int(x / self.tam_celda)
        fila = min(fila, self.filas - 1)
        columna = min(columna, self.columnas - 1)
        return fila, columna

    def actualizar(self, agentes, dt=1.0):
        """
        Procesa el estado actual de los agentes y actualiza las métricas y clasificación.

        Parámetros:
            agentes: Lista de agentes. Cada agente puede ser:
                     - un dict: {'x': float, 'y': float, 'vx': float, 'vy': float, 'v_deseada': float}
                     - un objeto con atributos .x, .y, .vx, .vy, .v_deseada
                     - una fila de telemetría (tupla/array con x, y, vx, vy)
            dt: Paso de tiempo transcurrido desde la última actualización (segundos).

        Retorna:
            (estados, matriz_D):
                - estados: matriz (10, 15) con las etiquetas 'libre', 'acumulacion', 'critica'
                - matriz_D: matriz (10, 15) normalizada entre 0.0 y 1.0 para A*
        """
        dt = float(dt)

        # 1. Agrupar agentes por celda de 2x2 m
        conteo = np.zeros(self.forma, dtype=int)
        suma_v = np.zeros(self.forma, dtype=float)
        suma_v_des = np.zeros(self.forma, dtype=float)

        for ag in agentes:
            # Extracción flexible de coordenadas y velocidades
            if isinstance(ag, dict):
                x = float(ag.get('x', 0.0))
                y = float(ag.get('y', 0.0))
                vx = float(ag.get('vx', 0.0))
                vy = float(ag.get('vy', 0.0))
                v_des = float(ag.get('v_deseada', V_DESEADA_NOMINAL))
            elif hasattr(ag, 'x') and hasattr(ag, 'y'):
                x = float(ag.x)
                y = float(ag.y)
                vx = float(getattr(ag, 'vx', 0.0))
                vy = float(getattr(ag, 'vy', 0.0))
                v_des = float(getattr(ag, 'v_deseada', V_DESEADA_NOMINAL))
            elif isinstance(ag, (list, tuple, np.ndarray)) and len(ag) >= 4:
                # Caso telemetría: [id, x, y, vx, vy, ...] o [x, y, vx, vy]
                if len(ag) >= 6:  # Formato t, id, x, y, vx, vy
                    x, y, vx, vy = float(ag[2]), float(ag[3]), float(ag[4]), float(ag[5])
                else:
                    x, y, vx, vy = float(ag[0]), float(ag[1]), float(ag[2]), float(ag[3])
                v_des = V_DESEADA_NOMINAL
            else:
                continue

            celda = self.obtener_celda(x, y)
            if celda is None:
                continue

            f, c = celda
            conteo[f, c] += 1
            mod_v = math.hypot(vx, vy)
            suma_v[f, c] += mod_v
            suma_v_des[f, c] += v_des

        self.conteo_agentes = conteo

        # 2. Calcular densidades y velocidades promedio
        for f in range(self.filas):
            for c in range(self.columnas):
                area = self.area_util[f, c]
                n = conteo[f, c]

                if area > 0.0:
                    self.densidad[f, c] = n / area
                else:
                    self.densidad[f, c] = 0.0

                if n > 0:
                    self.velocidad_promedio[f, c] = suma_v[f, c] / n
                    v_des_ref = suma_v_des[f, c] / n
                else:
                    self.velocidad_promedio[f, c] = 0.0
                    v_des_ref = V_DESEADA_NOMINAL

                # Si es una celda completamente obstáculo
                if area <= 0.0:
                    self.estados[f, c] = ESTADO_OBSTACULO
                    self.estados_codigo[f, c] = CODIGO_ESTADO[ESTADO_OBSTACULO]
                    self.tiempo_bloqueo[f, c] = 0.0
                    self.matriz_D[f, c] = 1.0  # Máximo costo para rutas
                    continue

                # 3. Evaluación de condiciones de bloqueo temporal
                # Condición instantánea para ser candidata a congestión crítica:
                # - Densidad >= 2.0 agentes/m²
                # - Velocidad promedio <= 50% de la deseada
                condicion_critica_instantanea = (
                    self.densidad[f, c] >= self.umbral_critica and
                    self.velocidad_promedio[f, c] <= (self.factor_v_critica * v_des_ref)
                )

                if condicion_critica_instantanea:
                    self.tiempo_bloqueo[f, c] += dt
                else:
                    # Si fluye o la densidad baja, se reinicia el contador de bloqueo
                    self.tiempo_bloqueo[f, c] = 0.0

                # 4. Clasificación según reglas
                if self.tiempo_bloqueo[f, c] >= self.persistencia_min:
                    # Cumple densidad crítica, velocidad reducida y persistencia >= 3s
                    self.estados[f, c] = ESTADO_CRITICA
                    self.estados_codigo[f, c] = CODIGO_ESTADO[ESTADO_CRITICA]
                elif self.densidad[f, c] >= self.umbral_alerta:
                    # Alta densidad pero fluye o no ha cumplido 3 segundos de bloqueo
                    self.estados[f, c] = ESTADO_ACUMULACION
                    self.estados_codigo[f, c] = CODIGO_ESTADO[ESTADO_ACUMULACION]
                else:
                    # Tránsito libre
                    self.estados[f, c] = ESTADO_LIBRE
                    self.estados_codigo[f, c] = CODIGO_ESTADO[ESTADO_LIBRE]

                # 5. Cálculo de D(e, t) = min(1.0; densidad / 2.0)
                self.matriz_D[f, c] = min(1.0, self.densidad[f, c] / self.umbral_critica)

        return self.estados.copy(), self.matriz_D.copy()

    def obtener_matriz_D(self):
        """Devuelve la matriz D(e, t) de forma (10, 15) con valores en [0, 1]."""
        return self.matriz_D.copy()

    def obtener_estados(self):
        """Devuelve la matriz de estados ('libre', 'acumulacion', 'critica')."""
        return self.estados.copy()

    def obtener_metricas_resumen(self):
        """
        Retorna estadísticas clave del diagnóstico para la telemetría y el informe.
        """
        mascara_transitable = self.area_util > 0.0
        densidades_validas = self.densidad[mascara_transitable]

        num_libres = int(np.sum(self.estados == ESTADO_LIBRE))
        num_acumulacion = int(np.sum(self.estados == ESTADO_ACUMULACION))
        num_criticas = int(np.sum(self.estados == ESTADO_CRITICA))

        densidad_max = float(np.max(densidades_validas)) if len(densidades_validas) > 0 else 0.0
        densidad_media = float(np.mean(densidades_validas)) if len(densidades_validas) > 0 else 0.0

        idx_max = np.unravel_index(np.argmax(self.densidad), self.forma)
        celda_max_x = (idx_max[1] + 0.5) * self.tam_celda
        celda_max_y = (idx_max[0] + 0.5) * self.tam_celda

        return {
            'total_agentes': int(np.sum(self.conteo_agentes)),
            'celdas_libres': num_libres,
            'celdas_acumulacion': num_acumulacion,
            'celdas_criticas': num_criticas,
            'densidad_maxima': round(densidad_max, 3),
            'densidad_media': round(densidad_media, 3),
            'celda_peor_congestion': (idx_max[0], idx_max[1]),
            'coordenada_peor_congestion': (celda_max_x, celda_max_y),
            'max_tiempo_bloqueo': round(float(np.max(self.tiempo_bloqueo)), 2)
        }

    def dibujar_diagnostico(self, agentes=None, archivo=None, mostrar=True, titulo=None):
        """
        Genera una visualización del estado de las zonas y mapa de calor de densidad.
        """
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        from matplotlib.patches import Patch

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # --- Subplot 1: Clasificación de Zonas por Reglas ---
        # Códigos: -1: pared (gris oscuro), 0: libre (verde), 1: acumulación (amarillo), 2: crítica (rojo)
        colores_estados = ['#37474F', '#A5D6A7', '#FFE082', '#EF5350']
        cmap_estados = ListedColormap(colores_estados)

        matriz_plot_estados = self.estados_codigo.copy()
        # Mapear -1 a 0, 0 a 1, 1 a 2, 2 a 3 para el colormap
        matriz_plot_idx = np.zeros(self.forma, dtype=int)
        matriz_plot_idx[matriz_plot_estados == -1] = 0
        matriz_plot_idx[matriz_plot_estados == 0] = 1
        matriz_plot_idx[matriz_plot_estados == 1] = 2
        matriz_plot_idx[matriz_plot_estados == 2] = 3

        im1 = ax1.imshow(matriz_plot_idx, origin='lower',
                         extent=(0, self.ancho, 0, self.alto),
                         cmap=cmap_estados, vmin=0, vmax=3, interpolation='nearest')

        # Dibujar cuadrícula de 2x2 m
        ax1.set_xticks(np.arange(0, self.ancho + 1, self.tam_celda))
        ax1.set_yticks(np.arange(0, self.alto + 1, self.tam_celda))
        ax1.grid(color='gray', linestyle=':', linewidth=0.5, alpha=0.7)

        # Dibujar agentes si se proporcionan
        if agentes is not None:
            xs, ys = [], []
            for ag in agentes:
                if isinstance(ag, dict):
                    xs.append(float(ag.get('x', 0.0)))
                    ys.append(float(ag.get('y', 0.0)))
                elif hasattr(ag, 'x') and hasattr(ag, 'y'):
                    xs.append(float(ag.x))
                    ys.append(float(ag.y))
                elif isinstance(ag, (list, tuple, np.ndarray)):
                    if len(ag) >= 6:
                        xs.append(float(ag[2]))
                        ys.append(float(ag[3]))
                    elif len(ag) >= 2:
                        xs.append(float(ag[0]))
                        ys.append(float(ag[1]))
            ax1.scatter(xs, ys, c='navy', s=12, alpha=0.8, edgecolors='none', label='Agentes')

        elementos_leyenda = [
            Patch(facecolor='#A5D6A7', edgecolor='black', label=f'Libre (< {self.umbral_alerta} ag/m²)'),
            Patch(facecolor='#FFE082', edgecolor='black', label=f'Acumulación (≥ {self.umbral_alerta} ag/m²)'),
            Patch(facecolor='#EF5350', edgecolor='black', label=f'Crítica (≥ {self.umbral_critica} ag/m² + ≤ 50% vel + ≥ 3s)'),
            Patch(facecolor='#37474F', edgecolor='black', label='Pared / Obstáculo')
        ]
        ax1.legend(handles=elementos_leyenda, loc='upper left', fontsize=8, framealpha=0.9)
        ax1.set_title('Clasificación de Zonas (Diagnóstico)', fontsize=11, fontweight='bold')
        ax1.set_xlabel('Coordenada X (m)')
        ax1.set_ylabel('Coordenada Y (m)')

        # --- Subplot 2: Matriz de Costo D(e, t) para A* ---
        im2 = ax2.imshow(self.matriz_D, origin='lower',
                         extent=(0, self.ancho, 0, self.alto),
                         cmap='YlOrRd', vmin=0.0, vmax=1.0, interpolation='nearest')
        ax2.set_xticks(np.arange(0, self.ancho + 1, self.tam_celda))
        ax2.set_yticks(np.arange(0, self.alto + 1, self.tam_celda))
        ax2.grid(color='gray', linestyle=':', linewidth=0.5, alpha=0.7)

        # Marcar valores de D en cada celda
        for f in range(self.filas):
            for c in range(self.columnas):
                if self.area_util[f, c] > 0:
                    val = self.matriz_D[f, c]
                    if val > 0.05:
                        color_t = 'white' if val > 0.6 else 'black'
                        ax2.text((c + 0.5) * self.tam_celda, (f + 0.5) * self.tam_celda,
                                 f"{val:.2f}", ha='center', va='center',
                                 color=color_t, fontsize=7, fontweight='bold')

        cbar2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
        cbar2.set_label(r'Factor de costo $D(e, t) = \min(1, \mathrm{densidad}/2.0)$', fontsize=9)

        ax2.set_title('Matriz de Costo $D(e, t)$ para A*', fontsize=11, fontweight='bold')
        ax2.set_xlabel('Coordenada X (m)')
        ax2.set_ylabel('Coordenada Y (m)')

        tit = titulo or 'Diagnóstico de Congestión en Cuadrícula de 2x2 m'
        fig.suptitle(tit, fontsize=13, fontweight='bold')
        plt.tight_layout()

        if archivo:
            Path(archivo).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(archivo, dpi=300, bbox_inches='tight')
            print(f"[Diagnóstico] Gráfico guardado en: {archivo}")

        if mostrar:
            plt.show()
        else:
            plt.close(fig)
