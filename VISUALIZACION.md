# Visualización con Pygame

Instalar: `python -m pip install -r requirements.txt`.
En Python 3.14 se usa pygame-ce (misma importación `pygame`), pues la
instalación de pygame 2.6.1 desde fuentes falló en este equipo.

Ejecutar `python demo_visualizacion.py`. H alterna densidad, S guarda una
captura con fecha en `capturas/`, Esc cierra. La demo usa datos ficticios
estáticos: tiempo 42.5 s, nueve activos y un llegado. No simula movimiento.

Para una captura sin ventana:
`python demo_visualizacion.py --sin-ventana --calor --captura capturas/demo_visualizacion.png`

## Contrato de integración

`main.py` y `modulos/entorno.py` conservan su comportamiento original.
Crear una `Visualizacion(entorno)` en el hilo principal y, en cada frame:

```python
from modulos.visualizacion import AgenteVisual, Visualizacion

vista = Visualizacion(entorno)
try:
    while vista.procesar_eventos():
        # El motor externo actualiza sus agentes y su reloj aquí.
        instantaneas = [AgenteVisual((2.5, 4.5), 0.7, 1.4)]
        vista.dibujar(instantaneas, tiempo_simulado=42.5, llegados=0)
        # Limitar FPS desde el bucle del motor.
finally:
    vista.cerrar()
```

Si el motor ya llama a `pygame.event.get()`, pasar esa misma lista a
`vista.procesar_eventos(eventos)` para que ambos componentes reciban los
eventos. La vista devuelve `False` al cerrar la ventana o pulsar Esc.
El panel confirma las capturas guardadas; la ruta exacta queda disponible
en `vista.ultima_captura`.

El ejemplo anterior contiene datos ficticios. La vista también acepta directamente
la lista `agentes` de Sthaicy: objetos con `x`, `y`, `vx`, `vy`, `v_deseada` y
`radio`. Calcula la rapidez como `hypot(vx, vy)` y copia el estado por frame.
Respeta `activo` y `llegado`; si faltan, supone activo y no llegado. No deduce
llegadas por proximidad a la salida. Inactivos y llegados no se dibujan ni
contribuyen a densidad. El panel cuenta solo activos que no han llegado.
Si el motor elimina agentes al llegar, pasar el total mediante `llegados`.

Posiciones `(x, y)` en metros: origen inferior izquierdo, ver `origin='lower'`
en `Entorno.dibujar_mapa`. La conversión a pantalla invierte Y. Las paredes
ocupan la celda completa de 1×1 m en `mapa[fila, columna]`.

`densidad` opcional: matriz `[fila, columna]` en personas/m² con celdas de
2×2 m, forma `(10, 15)` para este recinto. Fila cero corresponde al borde
inferior. Si se omite, la vista cuenta agentes activos por celda y divide por
su área; esto es una instantánea, no un promedio temporal. La escala fija de
calor va de 0 a 4 personas/m² y satura por encima de 4. Se dibuja debajo de
paredes y agentes. Velocidad deseada cero se muestra en gris.

Comprobaciones: `python pruebas_visualizacion.py`, `python pruebas_entorno.py`,
`python prueba_dos_rutas.py`, `python prueba_compatibilidad_astar.py`.

## Integración en el repositorio clonado

La carpeta `simulacion-multitudes-ia` contiene la demo integrada y una copia
del módulo de visualización. Su `main.py` se conserva. Desde la carpeta padre:

```powershell
.venv/Scripts/python.exe simulacion-multitudes-ia/demo_visualizacion.py --calor
```

La demo genera 40 agentes (también admite `--cantidad 80` o `120`) con semilla
42. Usa `MotorAgentes.actualizar(0.1)` y rutas A* fijas (modo A), sin reimplementar
movimiento. Muestra `motor.tiempo`. El calor utiliza `diagnostico.densidad`, en
personas/m² y calculada por área útil; se actualiza cada segundo simulado.
La matriz normalizada `D` de navegación no es una densidad y no se pasa a la vista.

```powershell
.venv/Scripts/python.exe simulacion-multitudes-ia/demo_visualizacion.py --sin-ventana --frames 100 --calor --captura simulacion-multitudes-ia/capturas/visualizacion_integrada.png
```

Pruebas en el clon: `pruebas_visualizacion.py` y
`pruebas_visualizacion_integrada.py`. La segunda usa los módulos reales de
agentes, navegación y diagnóstico y comprueba que dibujar no los modifica.

El A* del ZIP de Keyla coincide con el del clon tras normalizar finales de línea;
no fue necesario sobrescribirlo. La demo integrada es una prueba con datos
iniciales generados, no una validación experimental. Queda fuera de esta demo
la navegación adaptativa B y la calibración PSO.
