"""Registro y métricas de multitudes. Responsable: Flores Choquetopa Nicole.

No modifica los agentes ni depende del renderizado. Coordenadas en metros,
velocidades en m/s y tiempos en segundos de simulación.
"""

import csv
import math
from pathlib import Path

import numpy as np


COLUMNAS = ('t', 'id', 'x', 'y', 'vx', 'vy', 'dist_vecino_medio', 't_bloqueo')


def _leer(agente, campo, defecto=None):
    return agente.get(campo, defecto) if isinstance(agente, dict) else getattr(agente, campo, defecto)


def _activo(agente):
    return bool(_leer(agente, 'activo', True)) and not bool(_leer(agente, 'llegado', False))


class Telemetria:
    """Acumula un episodio; crear una instancia nueva para cada ejecución.

    Llamar a registrar después de diez pasos físicos de 0.1 s, pasando la
    lista COMPLETA del motor para observar también las llegadas. Cada llamada
    registra una muestra, sin temporizador automático. dt_muestreo es el
    intervalo representado por la velocidad observada (aproximación discreta).
    Los tiempos t deben ser estrictamente crecientes para evitar duplicados.

    registros contiene acumuladores por id; filas conserva copias escalares
    de las muestras activas. obtener_posiciones_np() sin argumentos devuelve
    una copia del último muestreo, no referencias al estado mutable del motor.
    """

    def __init__(self, entorno=None):
        self.entorno = entorno
        self.filas = []
        self.registros = {}
        self.solapamientos_instante = 0
        self.solapamientos_total = 0
        self._posiciones = np.empty((0, 2), dtype=np.float64)
        self._ultimo_t = None

    def registrar(self, t: float, agentes: list, dt_muestreo: float = 1.0):
        """Registra activos, bloqueo y llegadas sin alterar objetos/diccionarios.

        Un par superpuesto durante varias muestras se cuenta en cada una;
        solapamientos_total es una suma de pares por muestra, no pares únicos.
        """
        t, dt_muestreo = float(t), float(dt_muestreo)
        if not math.isfinite(t) or t < 0:
            raise ValueError('t debe ser finito y no negativo')
        if not math.isfinite(dt_muestreo) or dt_muestreo <= 0:
            raise ValueError('dt_muestreo debe ser finito y positivo')
        if self._ultimo_t is not None and t <= self._ultimo_t:
            raise ValueError('Los tiempos de muestreo deben ser estrictamente crecientes')

        # Validar la muestra completa antes de modificar los acumuladores.
        ids, activos, llegadas = set(), [], {}
        for agente in agentes:
            aid = _leer(agente, 'id')
            if isinstance(aid, (bool, np.bool_)) or not isinstance(aid, (int, np.integer)):
                raise ValueError('Cada agente debe tener un id entero')
            aid = int(aid)
            if aid in ids:
                raise ValueError('Los identificadores deben ser únicos en cada muestra')
            ids.add(aid)
            if _leer(agente, 'llegado', False):
                llegada = _leer(agente, 'tiempo_llegada')
                if llegada is None or not math.isfinite(llegada) or not 0 <= llegada <= t + 1e-9:
                    raise ValueError('Un agente llegado requiere tiempo_llegada válido, entre 0 y t')
                llegadas[aid] = float(llegada)
            if _activo(agente):
                valores = [float(_leer(agente, campo))
                           for campo in ('x', 'y', 'vx', 'vy', 'v_deseada', 'radio')]
                if not all(map(math.isfinite, valores)) or min(valores[4:]) <= 0:
                    raise ValueError('Estado activo finito, radio y velocidad deseada positivos requeridos')
                activos.append((aid, *valores))

        posiciones = np.array([[a[1], a[2]] for a in activos], dtype=np.float64).reshape(-1, 2)
        n = len(activos)
        distancias = np.linalg.norm(posiciones[:, None, :] - posiciones[None, :, :], axis=2)
        medias = distancias.sum(axis=1) / (n - 1) if n > 1 else np.zeros(n)
        radios = np.array([a[6] for a in activos])
        solapamientos = int(np.count_nonzero(np.triu(distancias < radios[:, None] + radios[None, :], k=1)))

        for aid in ids:
            self.registros.setdefault(aid, {'t_bloqueo': 0.0, 'tiempo_transito': None})
        for aid, llegada in llegadas.items():
            self.registros[aid]['tiempo_transito'] = llegada
        for i, (aid, x, y, vx, vy, deseada, _) in enumerate(activos):
            registro = self.registros[aid]
            if math.hypot(vx, vy) < 0.5 * deseada:
                registro['t_bloqueo'] += dt_muestreo
            self.filas.append(dict(zip(COLUMNAS, (
                t, aid, x, y, vx, vy, float(medias[i]), registro['t_bloqueo']))))
        self._posiciones = posiciones
        self.solapamientos_instante = solapamientos
        self.solapamientos_total += solapamientos
        self._ultimo_t = t

    def obtener_posiciones_np(self, agentes_activos=None) -> np.ndarray:
        """Devuelve float64 (N, 2), filtrando activos si se pasa una lista.

        Con una lista explícita consulta el estado actual sin registrar ni
        acumular métricas; sin argumentos utiliza el último muestreo.
        """
        if agentes_activos is None:
            return self._posiciones.copy()
        posiciones = np.array([[float(_leer(a, 'x')), float(_leer(a, 'y'))]
                               for a in agentes_activos if _activo(a)],
                              dtype=np.float64).reshape(-1, 2)
        if not np.isfinite(posiciones).all():
            raise ValueError('Las posiciones deben ser finitas')
        return posiciones

    def exportar_csv(self, ruta_csv: str):
        """Escribe todas las filas con encabezado fijo, incluso si no hay datos."""
        ruta = Path(ruta_csv)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open('w', newline='', encoding='utf-8') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
            escritor.writeheader()
            escritor.writerows(self.filas)

    def obtener_metricas_episodio(self, total_agentes: int, duracion_total: float) -> dict:
        """Métricas para costo_J, calculadas sobre toda la población inicial.

        Tránsito medio: llegada exacta o duracion_total para cada no llegado
        (180 s en un episodio oficial; 20 s en la demo corta). Espera media:
        bloqueo muestreado acumulado / total_agentes. Los ids no observados
        cuentan como no llegados con espera cero. activos_final significa
        pendientes de completar: total_agentes - llegados. Episodio vacío:
        promedios y tasa de finalización iguales a cero.
        """
        if isinstance(total_agentes, (bool, np.bool_)) or not isinstance(total_agentes, (int, np.integer)):
            raise ValueError('total_agentes debe ser un entero no negativo')
        duracion_total = float(duracion_total)
        if total_agentes < len(self.registros) or total_agentes < 0:
            raise ValueError('total_agentes no puede ser menor que la población registrada')
        if not math.isfinite(duracion_total) or duracion_total < 0:
            raise ValueError('duracion_total debe ser finita y no negativa')
        if self._ultimo_t is not None and duracion_total + 1e-9 < self._ultimo_t:
            raise ValueError('La duración no puede preceder al último muestreo')
        llegadas = [r['tiempo_transito'] for r in self.registros.values()
                    if r['tiempo_transito'] is not None]
        pendientes = int(total_agentes) - len(llegadas)
        espera = sum(r['t_bloqueo'] for r in self.registros.values())
        return {
            'tiempo_transito': float((sum(llegadas) + pendientes * duracion_total) / total_agentes) if total_agentes else 0.0,
            'tiempo_espera': float(espera / total_agentes) if total_agentes else 0.0,
            'solapamientos': self.solapamientos_total,
            'tasa_finalizacion': float(len(llegadas) / total_agentes) if total_agentes else 0.0,
            'llegados': len(llegadas),
            'activos_final': pendientes,
        }


def _prueba_autonoma():
    from .agentes import MotorAgentes, generar_agentes
    from .entorno import Entorno

    entorno = Entorno(configuracion='configuracion.json')
    agentes = generar_agentes(entorno, cantidad=40, semilla=42)
    motor = MotorAgentes(entorno, agentes)
    telemetria = Telemetria(entorno)
    for tick in range(200):
        motor.actualizar(dt=0.1)
        if (tick + 1) % 10 == 0:
            telemetria.registrar((tick + 1) / 10, agentes)
            posiciones = telemetria.obtener_posiciones_np()
            assert posiciones.shape == (len(motor.agentes_activos), 2)
            assert posiciones.dtype == np.float64 and np.isfinite(posiciones).all()
    ruta = 'capturas/telemetria_ejemplo.csv'
    telemetria.exportar_csv(ruta)
    print('Primeras 10 filas de ' + ruta + ':')
    with open(ruta, encoding='utf-8', newline='') as archivo:
        lector = csv.reader(archivo)
        print(','.join(next(lector)))
        for _, fila in zip(range(10), lector):
            print(','.join(fila))
    metricas = telemetria.obtener_metricas_episodio(40, 20.0)
    assert 0 <= metricas['tasa_finalizacion'] <= 1
    assert metricas['llegados'] + metricas['activos_final'] == 40
    print('Filas registradas:', len(telemetria.filas))
    print('Métricas finales:', metricas)


if __name__ == '__main__':
    _prueba_autonoma()
