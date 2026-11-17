"""Motor de agentes de Jhosselin Sthaicy Bustamante Escobar.

Coordenadas en metros y velocidades en m/s. No depende de Pygame,
telemetría ni DBSCAN; reutiliza las rutas del módulo de Keyla.
"""

from dataclasses import dataclass, field
import math

import numpy as np

from .navegacion_astar import NavegadorAdaptativo


@dataclass
class Agente:
    id: int
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    v_deseada: float = 1.2
    radio: float = 0.25
    destino: tuple | None = None
    ruta: list = field(default_factory=list)
    activo: bool = True
    llegado: bool = False
    tiempo_llegada: float | None = None

    def __post_init__(self):
        valores = (self.x, self.y, self.vx, self.vy, self.v_deseada, self.radio)
        if not all(math.isfinite(v) for v in valores):
            raise ValueError('El estado del agente debe ser finito')
        if self.radio <= 0 or self.v_deseada <= 0:
            raise ValueError('Radio y velocidad deseada deben ser positivos')
        if self.destino is not None:
            if len(self.destino) != 2 or not all(map(math.isfinite, self.destino)):
                raise ValueError('destino debe ser un par finito (x, y)')
            self.destino = tuple(self.destino)

    @property
    def velocidad(self):
        return math.hypot(self.vx, self.vy)


def _rectangulos(entorno):
    """Obstáculos físicos [xmin, ymin, xmax, ymax], no índices de matriz."""
    celdas = entorno.obstaculos()
    origen = celdas[:, ::-1].astype(float) * entorno.tam_celda
    return np.column_stack((origen, origen + entorno.tam_celda))


def posicion_valida(entorno, x, y, radio=0.25):
    """Comprueba el disco completo contra paredes y límites del recinto."""
    if not all(map(math.isfinite, (x, y, radio))) or radio <= 0:
        return False
    if not (radio <= x <= entorno.ancho - radio and
            radio <= y <= entorno.alto - radio):
        return False
    rect = _rectangulos(entorno)
    cercano = np.clip([x, y], rect[:, :2], rect[:, 2:])
    return bool(np.all(np.sum((cercano - [x, y]) ** 2, axis=1) >= radio**2 - 1e-12))


def generar_agentes(entorno, cantidad=40, semilla=42, zona=None):
    """Crea una lista de Agente sin solapamientos en la zona de entrada.

    zona opcional: (xmin, ymin, xmax, ymax), límites para los centros.
    La zona por defecto ocupa hasta 7 m a la derecha de la entrada y
    +/-6 m verticales. Se muestrea una retícula de 0.60 m con jitter
    de +/-0.02 m y se eligen sitios sin reemplazo con RNG local.
    """
    if isinstance(cantidad, bool) or not isinstance(cantidad, (int, np.integer)) or cantidad < 0:
        raise ValueError('cantidad debe ser un entero no negativo')
    if zona is None:
        ex, ey = entorno.entrada
        zona = (max(0.5, ex - 0.5), max(0.5, ey - 6),
                min(entorno.ancho - 0.5, ex + 7), min(entorno.alto - 0.5, ey + 6))
    if len(zona) != 4 or not all(map(math.isfinite, zona)):
        raise ValueError('zona debe contener cuatro límites finitos')
    xmin, ymin, xmax, ymax = zona
    if xmin >= xmax or ymin >= ymax:
        raise ValueError('zona debe tener área positiva')
    rng = np.random.default_rng(semilla)
    sitios = []
    for y in np.arange(ymin + 0.02, ymax - 0.019, 0.60):
        for x in np.arange(xmin + 0.02, xmax - 0.019, 0.60):
            px, py = np.array([x, y]) + rng.uniform(-0.02, 0.02, 2)
            if posicion_valida(entorno, px, py):
                sitios.append((float(px), float(py)))
    if cantidad > len(sitios):
        raise ValueError(f'La zona admite {len(sitios)} agentes, se pidieron {cantidad}')
    indices = rng.choice(len(sitios), size=cantidad, replace=False)
    return [Agente(id=i, x=sitios[k][0], y=sitios[k][1],
                   v_deseada=float(rng.uniform(0.9, 1.5)), destino=entorno.destino)
            for i, k in enumerate(indices)]


def _limitar(vectores, limite):
    norma = np.linalg.norm(vectores, axis=1)
    return vectores * np.minimum(1.0, limite / np.maximum(norma, 1e-12))[:, None]


class MotorAgentes:
    """Fi = ko*F_objetivo + ks*F_separacion + kr*F_obstaculos.

    Conserva la identidad de la lista y de sus objetos. El integrador limita
    aceleración y velocidad; una restricción geométrica adicional cancela
    desplazamientos con colisión (contacto inelástico, frenada instantánea).
    Los agentes llegados permanecen en la lista pero dejan de participar.
    """

    def __init__(self, entorno, agentes, ko=1.0, ks=1.0, kr=1.0,
                 velocidad_max=1.5, aceleracion_max=3.0, relajacion=0.5,
                 tolerancia_ruta=0.25, tolerancia_llegada=0.5):
        parametros = (ko, ks, kr, velocidad_max, aceleracion_max, relajacion,
                      tolerancia_ruta, tolerancia_llegada)
        if not all(map(math.isfinite, parametros)) or min(ko, ks, kr) < 0:
            raise ValueError('Los pesos deben ser finitos y no negativos')
        if min(parametros[3:]) <= 0:
            raise ValueError('Límites, relajación y tolerancias deben ser positivos')
        if len({a.id for a in agentes}) != len(agentes):
            raise ValueError('Los identificadores deben ser únicos')
        self.entorno, self.agentes = entorno, agentes
        self.ko, self.ks, self.kr = ko, ks, kr
        self.velocidad_max, self.aceleracion_max = velocidad_max, aceleracion_max
        self.relajacion = relajacion
        self.tolerancia_ruta, self.tolerancia_llegada = tolerancia_ruta, tolerancia_llegada
        self.tiempo = 0.0
        for a in agentes:
            if a.destino is None:
                a.destino = tuple(entorno.destino)
            if not posicion_valida(entorno, *a.destino, a.radio):
                raise ValueError(f'Destino inválido del agente {a.id}')
            if a.activo and not posicion_valida(entorno, a.x, a.y, a.radio):
                raise ValueError(f'Posición inválida del agente {a.id}')
            if a.velocidad > velocidad_max + 1e-12:
                raise ValueError(f'Velocidad inicial excesiva del agente {a.id}')
        activos = self.agentes_activos
        for i, a in enumerate(activos):
            if any(math.hypot(a.x - b.x, a.y - b.y) < a.radio + b.radio - 1e-10
                   for b in activos[:i]):
                raise ValueError('Los agentes iniciales se solapan')
        # Reutiliza A* de Keyla; no implementa ni calibra navegación adaptativa.
        nav = NavegadorAdaptativo(entorno, modo='A')
        for a in activos:
            if not a.ruta and not nav.asignar_ruta_inicial(a):
                raise ValueError(f'No existe ruta para el agente {a.id}')

    @property
    def agentes_activos(self):
        """Lista nueva con referencias a los agentes aún presentes en el recinto."""
        return [a for a in self.agentes if a.activo and not a.llegado]

    def _objetivo(self, a, rect):
        # Keyla puede reemplazar a.ruta: no se mantiene un índice oculto obsoleto.
        # La separación puede desplazar al agente más allá de un waypoint.
        # Mirar hasta 1.5 m por delante suaviza el seguimiento de la retícula;
        # solo se omiten puntos si el disco puede recorrer el segmento libre.
        if len(a.ruta) > 1:
            distancias = [math.hypot(p[0] - a.x, p[1] - a.y) for p in a.ruta]
            cercano = int(np.argmin(distancias))
            candidatos = [k for k in range(cercano, len(a.ruta)) if distancias[k] <= 1.5]
            for k in reversed(candidatos):
                if k and self._trayectoria_libre(np.array([a.x, a.y]), np.array(a.ruta[k]), a.radio, rect):
                    del a.ruta[:k]
                    break
        while a.ruta and math.hypot(a.ruta[0][0] - a.x, a.ruta[0][1] - a.y) <= self.tolerancia_ruta:
            a.ruta.pop(0)
        if len(a.ruta) == 1 and self.entorno.obtener_celda(*a.ruta[0]) == self.entorno.obtener_celda(*a.destino):
            a.ruta.pop(0)
        # El centro de la última celda no coincide necesariamente con el destino.
        return a.ruta[0] if a.ruta else a.destino

    def _fuerzas(self, activos, pos, vel, radios, rect):
        objetivos = np.array([self._objetivo(a, rect) for a in activos])
        delta = objetivos - pos
        dist = np.linalg.norm(delta, axis=1)
        deseadas = np.array([min(a.v_deseada, self.velocidad_max) for a in activos])
        # Solo frenar al acercarse al destino final, no ante cada celda de A*.
        for i, a in enumerate(activos):
            if not a.ruta:
                deseadas[i] = min(deseadas[i], dist[i] / self.relajacion)
        objetivo = (delta / np.maximum(dist[:, None], 1e-12) * deseadas[:, None] - vel) / self.relajacion

        diferencias = pos[:, None, :] - pos[None, :, :]
        distancias = np.linalg.norm(diferencias, axis=2)
        huecos = distancias - radios[:, None] - radios[None, :]
        intensidad = 4.0 * np.exp(np.clip(-huecos / 0.15, -50, 5))
        intensidad[huecos > 0.6] = 0
        np.fill_diagonal(intensidad, 0)
        separacion = np.sum(diferencias / np.maximum(distancias[:, :, None], 1e-12) * intensidad[:, :, None], axis=1)

        obstaculos = np.zeros_like(pos)
        if len(rect):
            cercanos = np.clip(pos[:, None, :], rect[None, :, :2], rect[None, :, 2:])
            dif = pos[:, None, :] - cercanos
            dist_pared = np.linalg.norm(dif, axis=2)
            gap = dist_pared - radios[:, None]
            magnitud = 6.0 * np.exp(np.clip(-gap / 0.15, -50, 5))
            magnitud[gap > 0.6] = 0
            obstaculos += np.sum(dif / np.maximum(dist_pared[:, :, None], 1e-12) * magnitud[:, :, None], axis=1)
        # Las fronteras exteriores también son paredes.
        dist_borde = np.column_stack((pos[:, 0], self.entorno.ancho - pos[:, 0],
                                     pos[:, 1], self.entorno.alto - pos[:, 1])) - radios[:, None]
        mag = 6.0 * np.exp(np.clip(-dist_borde / 0.15, -50, 5))
        mag[dist_borde > 0.6] = 0
        obstaculos += mag @ np.array([[1, 0], [-1, 0], [0, 1], [0, -1]])
        return self.ko * objetivo + self.ks * separacion + self.kr * obstaculos

    def _trayectoria_libre(self, inicio, fin, radio, rect):
        if np.any(fin < radio) or np.any(fin > np.array([self.entorno.ancho, self.entorno.alto]) - radio):
            return False
        if not len(rect):
            return True
        # Primero descartar las cajas lejanas al segmento expandido por el radio.
        cerca = np.all(rect[:, 2:] >= np.minimum(inicio, fin) - radio, axis=1) & np.all(
            rect[:, :2] <= np.maximum(inicio, fin) + radio, axis=1)
        rect = rect[cerca]
        if not len(rect):
            return True
        # Distancia exacta segmento/rectángulo: intersección, extremos contra
        # caja y vértices contra segmento. Así se respetan esquinas redondeadas.
        bajo, alto = rect[:, :2], rect[:, 2:]
        entrada, salida = np.zeros(len(rect)), np.ones(len(rect))
        for eje in (0, 1):
            d = fin[eje] - inicio[eje]
            if abs(d) < 1e-14:
                fuera = (inicio[eje] < bajo[:, eje]) | (inicio[eje] > alto[:, eje])
                salida[fuera] = -1
            else:
                t1, t2 = (bajo[:, eje] - inicio[eje]) / d, (alto[:, eje] - inicio[eje]) / d
                entrada = np.maximum(entrada, np.minimum(t1, t2))
                salida = np.minimum(salida, np.maximum(t1, t2))
        if np.any(entrada <= salida):
            return False
        extremos = np.array([inicio, fin])
        cercanos = np.clip(extremos[:, None, :], bajo, alto)
        d2_extremos = np.min(np.sum((extremos[:, None, :] - cercanos)**2, axis=2))
        vertices = rect[:, [0, 1, 0, 3, 2, 1, 2, 3]].reshape(-1, 2)
        avance = fin - inicio
        t = np.clip((vertices - inicio) @ avance / max(float(avance @ avance), 1e-20), 0, 1)
        d2_vertices = np.min(np.sum((vertices - inicio - t[:, None]*avance)**2, axis=1))
        return min(d2_extremos, d2_vertices) >= radio**2 - 1e-12

    def actualizar(self, dt=0.1):
        """Avanza tiempo simulado, sin reloj ni dibujo; devuelve agentes activos.

        Para dt > 0.1 se subdivide. El consumidor debe llamar al diagnóstico
        cada segundo con dt=1 y pasar solamente agentes_activos.
        """
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('dt debe ser finito y positivo')
        pasos = max(1, math.ceil(dt / 0.1))
        h = dt / pasos
        for _ in range(pasos):
            self._paso(h)
        return self.agentes_activos

    def _paso(self, dt):
        activos = self.agentes_activos
        if not activos:
            self.tiempo += dt
            return
        pos = np.array([[a.x, a.y] for a in activos], dtype=float)
        vel = np.array([[a.vx, a.vy] for a in activos], dtype=float)
        radios = np.array([a.radio for a in activos])
        rect = _rectangulos(self.entorno)
        aceleracion = _limitar(self._fuerzas(activos, pos, vel, radios, rect), self.aceleracion_max)
        nueva_vel = _limitar(vel + aceleracion * dt, self.velocidad_max)
        propuesta = pos + nueva_vel * dt
        for i in range(len(activos)):
            if not self._trayectoria_libre(pos[i], propuesta[i], radios[i], rect):
                propuesta[i] = pos[i]
        # Distancia mínima relativa durante el paso (evita cruces entre agentes).
        # Repetir tras frenar: un agente detenido puede bloquear otra propuesta.
        for _ in range(len(activos)):
            cambio = propuesta - pos
            relativo = pos[:, None, :] - pos[None, :, :]
            dv = cambio[:, None, :] - cambio[None, :, :]
            t = np.clip(-np.sum(relativo * dv, axis=2) / np.maximum(np.sum(dv**2, axis=2), 1e-20), 0, 1)
            d2 = np.sum((relativo + t[:, :, None] * dv)**2, axis=2)
            choques = d2 < (radios[:, None] + radios[None, :] - 1e-10)**2
            np.fill_diagonal(choques, False)
            frenar = np.any(choques, axis=1) & np.any(cambio != 0, axis=1)
            if not np.any(frenar):
                break
            propuesta[frenar] = pos[frenar]
        # La velocidad pública siempre coincide con el desplazamiento realizado.
        real = (propuesta - pos) / dt
        self.tiempo += dt
        for i, a in enumerate(activos):
            a.x, a.y = map(float, propuesta[i])
            a.vx, a.vy = map(float, real[i])
            if math.hypot(a.x - a.destino[0], a.y - a.destino[1]) <= self.tolerancia_llegada:
                a.activo, a.llegado = False, True
                a.tiempo_llegada = self.tiempo
                a.vx = a.vy = 0.0
                a.ruta.clear()
