
# Motor del escenario
# Responsable: Padilla Alexander

from pathlib import Path

try:
    from .modulos.entorno import Entorno
except ImportError:
    from modulos.entorno import Entorno


def main():

    # Obtener la carpeta donde se encuentra main.py
    carpeta_proyecto = Path(__file__).resolve().parent

    # Construir la ruta completa de configuracion.json
    archivo_configuracion = carpeta_proyecto / "configuracion.json"

    # Crear el entorno
    entorno = Entorno(configuracion=str(archivo_configuracion))

    print("MOTOR DEL ESCENARIO")

    print("Dimensiones:", entorno.ancho, "x", entorno.alto)
    print("Cuadricula:", entorno.filas, "filas x", entorno.columnas, "columnas")
    print("Entrada:", entorno.entrada, "| Salida:", entorno.salida)
    print("Obstaculos:", len(entorno.obstaculos()))

    print("Pared (15,8):", entorno.es_transitable(15, 8))
    print("Paso principal (15,11):", entorno.es_transitable(15, 11))
    print("Paso alternativo (15,5):", entorno.es_transitable(15, 5))

    # Guardar imagen en la carpeta capturas
    ruta_imagen = carpeta_proyecto / "capturas" / "mapa_escenario.png"

    entorno.dibujar_mapa(
        archivo=str(ruta_imagen),
        mostrar=True
    )

    print("Imagen guardada en:", ruta_imagen)


if __name__ == "__main__":
    main()
