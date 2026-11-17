"""Comprobaciones de contrato y renderizado sin ventana real."""
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ['SDL_VIDEODRIVER'] = 'dummy'

import numpy as np
import pygame
from modulos.entorno import Entorno
from modulos.visualizacion import AgenteVisual, Visualizacion, color_velocidad


class PruebasVisualizacion(unittest.TestCase):
    def test_renderizado_y_controles(self):
        entorno = Entorno()
        mapa_original = entorno.obtener_mapa()
        with tempfile.TemporaryDirectory() as carpeta:
            vista = Visualizacion(entorno, carpeta_capturas=carpeta)
            try:
                agentes = [AgenteVisual((2.5, 4.5), 0, 1),
                           AgenteVisual((2.6, 4.6), 1, 1),
                           AgenteVisual((29, 11), 0, 1, True)]
                densidad = vista.densidad_agentes(agentes)
                self.assertEqual(densidad.shape, (10, 15))
                self.assertEqual(densidad[2, 1], .5)
                self.assertEqual(densidad.sum(), .5)
                self.assertEqual(vista.a_pantalla(0, 0), (32, 592))
                self.assertEqual(vista.a_pantalla(30, 20), (872, 32))
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h))
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s))
                self.assertTrue(vista.procesar_eventos())
                self.assertTrue(vista.mostrar_calor)
                vista.dibujar(agentes, 42.5)
                self.assertTrue(vista.ultima_captura.exists())
                self.assertEqual(vista.ultima_captura.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
                imagen = pygame.image.load(str(vista.ultima_captura))
                self.assertEqual(tuple(imagen.get_at(vista.a_pantalla(15.5, 8.5)))[:3],
                                 (57, 70, 83))
                self.assertEqual(tuple(imagen.get_at(vista.a_pantalla(2.5, 4.5)))[:3],
                                 color_velocidad(1, 1))
                with self.assertRaises(ValueError):
                    vista.dibujar(agentes, 0, densidad=np.zeros((20, 30)))
                np.testing.assert_array_equal(entorno.mapa, mapa_original)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                self.assertFalse(vista.procesar_eventos())
            finally:
                vista.cerrar()

    def test_colores(self):
        self.assertEqual(color_velocidad(0, 1), (230, 0, 55))
        self.assertEqual(color_velocidad(.5, 1), (230, 200, 55))
        self.assertEqual(color_velocidad(2, 1), (0, 200, 55))
        self.assertEqual(color_velocidad(0, 0), (130, 140, 150))

    def test_interfaz_sthaicy_sin_mutaciones(self):
        agente = SimpleNamespace(id=5, x=3, y=5, vx=-3, vy=4,
                                 v_deseada=6, radio=.4)
        original = vars(agente).copy()
        instantanea = AgenteVisual.desde_agente(agente)
        self.assertEqual(instantanea.velocidad_actual, 5)
        self.assertEqual(instantanea.radio, .4)
        agente.x = 9
        self.assertEqual(instantanea.posicion, (3, 5))
        agente.x = 3
        vista = Visualizacion(Entorno())
        try:
            inactivo = SimpleNamespace(**dict(original, id=6, activo=False))
            llegado = SimpleNamespace(**dict(original, id=7, llegado=True, activo=False))
            self.assertEqual(vista.densidad_agentes([agente, inactivo, llegado]).sum(), .25)
            vista.dibujar([agente, inactivo, llegado], 1)
            self.assertEqual(vars(agente), original)
            self.assertEqual(tuple(vista.pantalla.get_at(vista.a_pantalla(3.3, 5)))[:3],
                             color_velocidad(5, 6))
        finally:
            vista.cerrar()

    def test_eventos_compartidos_y_panel_a_escala_reducida(self):
        vista = Visualizacion(Entorno(), pixeles_por_metro=4)
        try:
            self.assertGreaterEqual(vista.pantalla.get_height(), 600)
            eventos = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h)]
            self.assertTrue(vista.procesar_eventos(eventos))
            self.assertTrue(vista.mostrar_calor)
            densidad = np.zeros((10, 15))
            densidad[0, 0] = 4
            vista.dibujar([], 0, llegados=7, densidad=densidad)
            self.assertEqual(tuple(vista.pantalla.get_at(vista.a_pantalla(1, 1)))[:3],
                             (255, 50, 45))
            self.assertEqual(tuple(vista.pantalla.get_at(vista.a_pantalla(1, 19)))[:3],
                             (255, 245, 220))
            self.assertTrue(vista.procesar_eventos([]))
            self.assertTrue(vista.mostrar_calor)
            self.assertFalse(vista.procesar_eventos([
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]))
        finally:
            vista.cerrar()


if __name__ == '__main__':
    unittest.main()
