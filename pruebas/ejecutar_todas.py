"""Ejecuta todas las pruebas, incluidas las que usan funciones y __main__."""

import os
from pathlib import Path
import subprocess
import sys


RAIZ = Path(__file__).resolve().parents[1]
PRUEBAS = (
    'prueba_compatibilidad_astar',
    'prueba_dos_rutas',
    'pruebas_agentes',
    'pruebas_diagnostico',
    'pruebas_entorno',
    'pruebas_integracion',
    'pruebas_navegacion',
    'pruebas_telemetria',
    'pruebas_visualizacion',
    'pruebas_visualizacion_integrada',
)


def main():
    entorno = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    entorno.setdefault('MPLBACKEND', 'Agg')
    fallos = []
    for numero, nombre in enumerate(PRUEBAS, 1):
        modulo = 'pruebas.' + nombre
        print(f'\n[{numero}/{len(PRUEBAS)}] python -m {modulo}', flush=True)
        resultado = subprocess.run([sys.executable, '-B', '-m', modulo],
                                   cwd=RAIZ, env=entorno)
        if resultado.returncode:
            fallos.append((modulo, resultado.returncode))
    if fallos:
        print('\nPruebas con errores:', fallos, flush=True)
        return 1
    print(f'\nSUITE COMPLETA: {len(PRUEBAS)}/{len(PRUEBAS)} scripts correctos.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
