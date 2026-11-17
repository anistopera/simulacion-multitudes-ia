from modulos.entorno import Entorno


def probar_entorno():
    e = Entorno()
    assert e.mapa.shape == (20, 30)
    assert e.obtener_celda(5.2, 6.8) == (6, 5)
    assert e.obtener_celda(30, 6) is None
    assert e.es_transitable(5, 5)
    assert not e.es_transitable(15, 8)
    assert all(e.es_transitable(15, y) for y in (10, 11, 4, 5, 6))
    assert len(e.obstaculos()) == 15
    assert not e.es_transitable(-1, 5)
    assert e.agregar_obstaculo(5, 5)
    assert not e.es_transitable(5, 5)
    assert e.quitar_obstaculo(5, 5)
    assert e.es_transitable(5, 5)
    assert not e.agregar_obstaculo(*e.entrada)
    assert Entorno(paso_principal=3).es_transitable(15, 12)
    print('Todas las pruebas del entorno fueron exitosas.')


if __name__ == '__main__':
    probar_entorno()
