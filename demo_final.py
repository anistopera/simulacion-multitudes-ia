# -*- coding: utf-8 -*-
"""
Demostración final del simulador V3 con un solo comando (o doble clic).

Qué hace, en orden:
  1. Verifica que estén instaladas las librerías (numpy, scikit-learn, matplotlib, pygame-ce).
  2. Verifica los archivos que necesita la defensa (mapa, interfaz web, theta de B+PSO).
  3. (Opcional) Corre las 13 pruebas y solo continúa si todas pasan.
  4. Abre la interfaz web local y el navegador. No escribe nada en capturas/.

Uso (desde la raíz del repositorio):
    python demo_final.py                    # abre la interfaz (S1, modo A, semilla 42)
    python demo_final.py --con-pruebas      # corre antes las 13 pruebas
    python demo_final.py --modo B_PSO --agentes 120 --semilla 42
    python demo_final.py --solo-verificar   # solo pasos 1-3, sin abrir la interfaz
    python demo_final.py --sin-navegador    # no abre el navegador (la URL se imprime)
"""
import argparse
import importlib
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

LIBRERIAS = (('numpy', 'numpy'), ('sklearn', 'scikit-learn'),
             ('matplotlib', 'matplotlib'), ('pygame', 'pygame-ce'))
ARCHIVOS = (('configuracion.json', 'mapa del recinto'),
            ('web/index.html', 'interfaz web'),
            ('web/app.js', 'interfaz web'),
            ('capturas/theta_optimo.json', 'theta calibrado para el modo B+PSO'))


def verificar_librerias():
    faltan = []
    for modulo, paquete in LIBRERIAS:
        try:
            importlib.import_module(modulo)
        except ImportError:
            faltan.append(paquete)
    if faltan:
        print('[ERROR] Faltan librerías:', ', '.join(faltan))
        print('        Instálalas con:  python -m pip install -r requirements.txt')
        return False
    print('[OK] Librerías instaladas')
    return True


def verificar_archivos():
    todo_ok = True
    for ruta, descripcion in ARCHIVOS:
        if (RAIZ / ruta).exists():
            print(f'[OK] {ruta} ({descripcion})')
        else:
            todo_ok = False
            print(f'[ERROR] Falta {ruta} ({descripcion})')
    return todo_ok


def correr_pruebas():
    print('\nCorriendo las 13 pruebas (unos 15 segundos)...', flush=True)
    resultado = subprocess.run([sys.executable, '-B', '-m', 'pruebas.ejecutar_todas'],
                               cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               text=True)
    if resultado.returncode:
        print('[ERROR] Hay pruebas que fallan. Detalle: python -m pruebas.ejecutar_todas')
        return False
    print('[OK] Suite completa: 13/13 scripts correctos')
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--modo', choices=('A', 'B', 'B_PSO'), default='A')
    parser.add_argument('--agentes', type=int, choices=(40, 80, 120), default=40)
    parser.add_argument('--semilla', type=int, default=42)
    parser.add_argument('--con-pruebas', action='store_true')
    parser.add_argument('--solo-verificar', action='store_true')
    parser.add_argument('--sin-navegador', action='store_true')
    args = parser.parse_args(argv)

    print('=== Simulador de multitudes V3: demostración final ===\n')
    if not (verificar_librerias() and verificar_archivos()):
        return 1
    if args.con_pruebas and not correr_pruebas():
        return 1
    if args.solo_verificar:
        print('\nTodo listo para la defensa.')
        return 0

    import main as principal
    from modulos import servidor_web
    escenario = next(e for e, n in principal.ESCENARIOS.items() if n == args.agentes)
    print('\nAtajos útiles: A/B/P cambian de modo, 1/2/3 el escenario, Espacio inicia o pausa,')
    print('H calor, C grupos, R rutas, S captura, ? muestra todos los atajos.\n')
    servidor_web.servir(principal, args.modo, escenario, args.semilla,
                        abrir=not args.sin_navegador)
    return 0


if __name__ == '__main__':
    codigo = 1
    try:
        codigo = main()
    except Exception as error:   # un doble clic en Windows cierra la ventana: avisar antes
        print('[ERROR]', error)
    if codigo and sys.stdin is not None and sys.stdin.isatty():
        input('\nPulsa Enter para cerrar...')
    raise SystemExit(codigo)
