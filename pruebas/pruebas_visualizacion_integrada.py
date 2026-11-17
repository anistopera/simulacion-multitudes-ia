"""Comprueba la vista con los módulos reales sin abrir una ventana."""
import os
import unittest
from copy import deepcopy

os.environ['SDL_VIDEODRIVER'] = 'dummy'

import numpy as np
from modulos.agentes import Agente, MotorAgentes, generar_agentes
from modulos.entorno import Entorno
from modulos.diagnostico import DiagnosticoCongestion
from modulos.visualizacion import AgenteVisual, Visualizacion


class PruebasIntegracion(unittest.TestCase):
    def test_motor_astar_diagnostico_y_vista(self):
        entorno = Entorno()
        agentes = generar_agentes(entorno, 40, semilla=42)
        motor = MotorAgentes(entorno, agentes)
        self.assertTrue(all(a.ruta for a in agentes))
        posiciones = [(a.x, a.y) for a in agentes]
        for _ in range(10):
            motor.actualizar(.1)
        self.assertNotEqual(posiciones, [(a.x, a.y) for a in agentes])
        diagnostico = DiagnosticoCongestion(entorno=entorno)
        diagnostico.actualizar(motor.agentes_activos, dt=1)
        estado = deepcopy([vars(a) for a in agentes])
        densidad = diagnostico.densidad.copy()
        mapa = entorno.mapa.copy()
        vista = Visualizacion(entorno)
        try:
            vista.mostrar_calor = True
            vista.dibujar(agentes, motor.tiempo, densidad=diagnostico.densidad)
            self.assertEqual([vars(a) for a in agentes], estado)
            np.testing.assert_array_equal(diagnostico.densidad, densidad)
            np.testing.assert_array_equal(entorno.mapa, mapa)
            for a in agentes:
                self.assertAlmostEqual(AgenteVisual.desde_agente(a).velocidad_actual, a.velocidad)
        finally:
            vista.cerrar()

    def test_llegado_e_inactivo_no_aumentan_densidad(self):
        agentes = [Agente(1, 2, 3), Agente(2, 2, 3, activo=False),
                   Agente(3, 2, 3, activo=False, llegado=True)]
        vista = Visualizacion(Entorno())
        try:
            self.assertEqual(vista.densidad_agentes(agentes).sum(), .25)
            vista.dibujar(agentes, 1)
        finally:
            vista.cerrar()


if __name__ == '__main__':
    unittest.main()
