
# ==================================================
# PRUEBA DE COMPATIBILIDAD DEL ENTORNO CON A*
# Proyecto: Simulacion de Multitudes
# Responsable: Padilla Alexander
# ==================================================

from collections import deque
from modulos.entorno import Entorno


# --------------------------------------------------
# FUNCION PARA VERIFICAR SI EXISTE UNA RUTA
# --------------------------------------------------

def verificar_ruta(entorno):

    inicio = entorno.obtener_celda(*entorno.entrada)
    destino = entorno.obtener_celda(*entorno.salida)

    cola = deque([inicio])
    visitados = {inicio}

    # Movimientos permitidos:
    # Abajo, arriba, derecha e izquierda
    movimientos = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1)
    ]

    while cola:

        fila, columna = cola.popleft()

        # Verificar si llegamos al destino
        if (fila, columna) == destino:
            return True

        # Revisar las celdas vecinas
        for df, dc in movimientos:

            nf = fila + df
            nc = columna + dc

            # Verificar limites del mapa
            if not (
                0 <= nf < entorno.filas
                and 0 <= nc < entorno.columnas
            ):
                continue

            # Evitar visitar la misma celda
            if (nf, nc) in visitados:
                continue

            # Convertir celda a coordenadas fisicas
            x = (nc + 0.5) * entorno.tam_celda
            y = (nf + 0.5) * entorno.tam_celda

            # Comprobar si se puede transitar
            if entorno.es_transitable(x, y):

                visitados.add((nf, nc))
                cola.append((nf, nc))

    # No existe una ruta disponible
    return False


# --------------------------------------------------
# PRUEBAS DE COMPATIBILIDAD CON A*
# --------------------------------------------------

def probar_compatibilidad():

    entorno = Entorno()

    print("================================")
    print(" COMPATIBILIDAD CON A*")
    print("================================")

    # 1. VERIFICAR DIMENSIONES

    print("\n1. DIMENSIONES")

    mapa = entorno.obtener_mapa()

    print("Filas:", mapa.shape[0])
    print("Columnas:", mapa.shape[1])

    assert mapa.shape == (20, 30)


    # 2. VERIFICAR ENTRADA Y SALIDA

    print("\n2. ENTRADA Y SALIDA")

    print("Entrada:", entorno.entrada)
    print("Salida:", entorno.salida)

    assert entorno.es_transitable(*entorno.entrada)
    assert entorno.es_transitable(*entorno.salida)


    # 3. VERIFICAR LOS PASOS

    print("\n3. PASOS DE LA BARRERA")

    principal = entorno.es_transitable(15, 11)
    alternativo = entorno.es_transitable(15, 5)
    pared = entorno.es_transitable(15, 8)

    print("Paso principal:", principal)
    print("Paso alternativo:", alternativo)
    print("Pared central:", pared)

    assert principal
    assert alternativo
    assert not pared


    # 4. VERIFICAR CONVERSION DE COORDENADAS

    print("\n4. CONVERSION DE COORDENADAS")

    celda = entorno.obtener_celda(15, 11)

    print("Posicion (15,11) -> celda:", celda)

    assert celda == (11, 15)


    # 5. VERIFICAR OBSTACULOS

    print("\n5. OBSTACULOS")

    obstaculos = entorno.obstaculos()

    print("Cantidad:", len(obstaculos))

    assert len(obstaculos) == 15


    # 6. VERIFICAR CONECTIVIDAD DEL MAPA

    print("\n6. CONECTIVIDAD DEL MAPA")

    ruta_disponible = verificar_ruta(entorno)

    print(
        "Existe ruta entrada-salida:",
        ruta_disponible
    )

    assert ruta_disponible


    # RESULTADO FINAL

    print("\n================================")
    print(" TODAS LAS PRUEBAS EXITOSAS")
    print(" COMPATIBILIDAD BASICA CON A* OK")
    print("================================")


# --------------------------------------------------
# EJECUCION PRINCIPAL
# --------------------------------------------------

if __name__ == "__main__":
    probar_compatibilidad()
