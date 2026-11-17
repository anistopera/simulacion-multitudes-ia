
# Prueba de las dos rutas del escenario
# Responsable: Padilla Alexander

from collections import deque
from modulos.entorno import Entorno


def existe_ruta(entorno):
    mapa = entorno.obtener_mapa()

    inicio = entorno.obtener_celda(*entorno.entrada)
    destino = entorno.obtener_celda(*entorno.salida)

    cola = deque([inicio])
    visitados = {inicio}

    movimientos = [
        (1, 0), (-1, 0),
        (0, 1), (0, -1)
    ]

    while cola:
        fila, columna = cola.popleft()

        if (fila, columna) == destino:
            return True

        for df, dc in movimientos:
            nf = fila + df
            nc = columna + dc

            if not (0 <= nf < mapa.shape[0]
                    and 0 <= nc < mapa.shape[1]):
                continue

            if (nf, nc) in visitados:
                continue

            if mapa[nf, nc] == 0:
                visitados.add((nf, nc))
                cola.append((nf, nc))

    return False


def probar_dos_rutas():
    print("===================================")
    print(" PRUEBA DE LAS DOS RUTAS")
    print("===================================")

    # Prueba 1: ambas rutas abiertas
    entorno = Entorno()
    resultado = existe_ruta(entorno)

    print("\n1. Ambas rutas abiertas:", resultado)
    assert resultado

    # Prueba 2: bloquear ruta alternativa
    entorno = Entorno()

    for y in range(4, 7):
        entorno.agregar_obstaculo(15, y)

    resultado = existe_ruta(entorno)

    print("2. Solo paso principal:", resultado)
    assert resultado

    # Prueba 3: bloquear paso principal
    entorno = Entorno()

    for y in range(10, 12):
        entorno.agregar_obstaculo(15, y)

    resultado = existe_ruta(entorno)

    print("3. Solo ruta alternativa:", resultado)
    assert resultado

    print("\nTODAS LAS PRUEBAS EXITOSAS")
    print("LAS DOS RUTAS SON TRANSITABLES")


if __name__ == "__main__":
    probar_dos_rutas()
