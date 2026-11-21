# AUDITORIA_UI — Interfaz web con controles (rama `feature/ui-controles-v3`)

> Fase 1 (solo lectura) aprobada; este documento se mantiene al día durante la implementación.

## Contexto

La interfaz actual es una ventana pygame sin botones; modo, escenario y semilla se eligen por flags. El objetivo es una UI web local con controles en pantalla, para la defensa offline. Python conserva toda la lógica; HTML/CSS/JS solo dibuja y envía controles. `--visualizar` sigue intacto como respaldo.

## Resumen de decisiones y hallazgos

1. **Reutilizar `ejecutar_episodio` con una vista inyectada**, sin copiar el ciclo de simulación. Cuesta unas 10 líneas en `main.py` y garantiza que la UI corra exactamente la misma lógica, incluido el B+PSO que agregue Jheycob.
2. **La UI no escribe en `capturas/`.** Sus CSV van a una carpeta temporal. Hoy una corrida sin `--visualizar` sobrescribe los CSV oficiales (ver A1).
3. **El rendimiento alcanza.** En S3, 60 s simulados, la física promedia 6–8 ms por tick y el JSON pesa unos 3,2 KB. Los recálculos de modo B llegan a ~93 ms, con picos aislados.
4. **`entorno.py` cumple la geometría.** `es_transitable` es O(1), pero **sí crea una tupla por llamada**. No conviene cambiarlo: no está en el ciclo caliente.
5. **"Solo Python y navegador" no alcanza:** NumPy y scikit-learn deben quedar instalados **antes** de la defensa, porque offline no se puede usar `pip`.

## Alertas

- **A1. CSV oficiales modificados en tu árbol.** `capturas/experimentos/S3_B_semilla42_{analisis,telemetria}.csv` aparecen modificados desde las 15:03. Las filas son equivalentes (diferencia máxima 1,5e-12; cambia CRLF y el redondeo del último dígito). La causa probable es `python main.py --modo B --agentes 120 --semilla 42`, que usa el mismo nombre que la batería. **No los incluyas en un commit.** También hay 3 CSV `*_visual*`/`resultado_*` sin seguimiento. No los toco.
- **A2. Contratos desactualizados en `AGENTS.md`.** Los estados reales son cadenas (`'critica'`), no `uint8`; el módulo real es `dbscan_deteccion.py`, no `clustering.py`; `Agente` no tiene `tiempo_viaje` ni `tiempo_espera`. La UI usa las firmas reales.
- **A3. Suite.** Agregar las pruebas nuevas la convierte en **11/11**. Los 10 scripts actuales no se alteran. El README dice "diez scripts" y habría que avisar a Nicole.

## 1. Inventario gráfico

### (a) Interfaz interactiva en vivo

| Archivo | Elementos | Acción |
|---|---|---|
| `modulos/visualizacion.py` | `AgenteVisual`, `color_velocidad`, `Visualizacion` (`procesar_eventos`, `dibujar`, `guardar_captura`, `cerrar`, `a_pantalla`, `rectangulo`, `densidad_agentes`) | No se toca |
| `main.py` | `_crear_visualizacion`, bloque visual de `ejecutar_episodio`, `--visualizar` | Cambio mínimo |
| `demos/demo_visualizacion.py` | Demo pygame | No se toca |
| `pruebas/pruebas_visualizacion.py`, `pruebas_visualizacion_integrada.py` | Contrato pygame | No se tocan |
| `pruebas/pruebas_integracion.py` | Contrato de vista en `main` | No se toca |

### (b) Figuras de análisis con Matplotlib (NO se tocan)

`main.generar_figura`, `Entorno.dibujar_mapa`, `DiagnosticoCongestion.dibujar_diagnostico`, `demos/demo_agentes.py`, `demos/demo_diagnostico.py`, `demos/demo_navegacion.py`, `scripts_analisis/figuras_dbscan.py` y las imágenes de `capturas/`.

### Archivos nuevos y modificados

- **Nuevos:** `web/index.html`, `web/estilos.css`, `web/app.js`, `modulos/servidor_web.py`, `pruebas/pruebas_interfaz_web.py`, `AUDITORIA_UI.md`.
- **Modificados:** `main.py` (mínimo), `pruebas/ejecutar_todas.py` (una línea).

## 2. Conexión actual entre vista y `main.py`

Dentro de `ejecutar_episodio` (`main.py:56`):

| Momento | Llamada | Dato |
|---|---|---|
| Creación | `_crear_visualizacion(entorno, carpeta, modo)` (`:47`, `:91`) | Devuelve `(vista, reloj)` |
| Antes del ciclo | `diagnostico.actualizar(activos, dt=0.0)` (`:95`) | Calor inicial sin acumular persistencia |
| Inicio de cada tick | `vis.procesar_eventos()` (`:97`) | `False` → `interrumpido=True` y corte |
| Tras física y análisis | `vis.dibujar(activos, motor.tiempo, llegados=, densidad=diagnostico.densidad)` (`:121`) | Activos, tiempo, llegados, densidad |
| Fin de tick | `reloj.tick(10)` (`:123`) | Limita a 10 ticks/s |
| Cierre | `vis.cerrar()` en `finally` (`:128`) | También ante excepción |

**Reutilización.** `procesar_eventos` es el punto ideal para los controles: si bloquea, pausa; si deja pasar un tick, hace paso a paso; si devuelve `False`, reinicia. Solo faltan el cuadro inicial (t=0, porque `dibujar` llega después del primer tick) y las celdas críticas, que `dibujar` no recibe. Ambos se resuelven con un `vista.conectar(motor, diagnostico)`.

## 3. Arquitectura recomendada

```text
Navegador (HTML/CSS/JS)            Python (stdlib + módulos existentes)
  canvas + paneles    GET /estado   ThreadingHTTPServer 127.0.0.1 (hilo principal)
  sondeo ~10 Hz     <-------------   último JSON ya serializado
  botones/teclas    POST /control -> SesionWeb (comandos con Condition)
                                       | hilo de simulación
                                       v
                                  main.ejecutar_episodio(..., vista=sesion)
```

Ajustes a tu propuesta, con motivo:

- **Una sola clase `SesionWeb`** implementa la interfaz de vista (`conectar`, `procesar_eventos`, `dibujar`, `tick`, `cerrar`) y los comandos.
- **El estado se serializa en el hilo de simulación**, tras cada tick. HTTP solo entrega los últimos bytes, así nunca lee agentes a medio actualizar.
- **Las capas viven en el navegador.** Calor, Grupos y Rutas no cambian la simulación, así que no pasan por `/control`. `S` exporta el canvas a PNG con `toBlob` (va a Descargas).
- **Las rutas son opcionales:** `/estado?rutas=1`, refrescadas a 1 Hz. Pesan hasta 36 KB, frente a 3 KB del estado normal.
- **Python envía `q = v/v_deseada`** ya calculado; JS solo lo convierte en color con la misma rampa de `color_velocidad`. No se importa `visualizacion.py`, para que la UI web no requiera pygame.

### Contrato JSON

```jsonc
// GET /estado
{ "fase": "listo|corriendo|pausado|terminado|error", "modo": "B", "escenario": "S2",
  "semilla": 42, "t": 12.3, "activos": 71, "llegados": 9, "total": 80, "criticas": 1,
  "agentes": [[id, x, y, q, tipo]],     // tipo: 2 núcleo, 1 frontera, 0 ruido
  "centros": [[x, y, tamano]], "densidad": [[...]],   // (10, 15), personas/m²
  "pso": { "disponible": false, "motivo": "..." }, "error": null }

// POST /control (Content-Type: application/json)
{ "accion": "iniciar|pausar|paso|reiniciar|configurar", "modo": "A", "escenario": "S1" }
```

El mapa (obstáculos, entrada, salida, dimensiones) se entrega una vez en `GET /config`.

### Seguridad y robustez, sin agregar complejidad

- Escucha solo en `127.0.0.1`.
- Lista blanca de 3 archivos estáticos, **sin** `SimpleHTTPRequestHandler`, que expondría el repo y `.git`.
- Valida `Host` y exige JSON en `/control`, para que una página externa abierta en el navegador no controle la simulación.
- Puerto 8765; si está ocupado, prueba los 10 siguientes.
- Un error en el hilo de simulación se muestra en la UI y permite reiniciar.

### Web vs. mejorar pygame

| Criterio | Web (recomendada) | Solo pygame |
|---|---|---|
| Calidad visual y controles | Botones y estados nativos de CSS | Widgets a mano |
| Dependencias nuevas | Ninguna | Ninguna |
| Riesgo principal | Hilos y acceso WSL → Windows | Ventana gráfica en WSL, layout rígido |
| Impacto en pruebas | Script nuevo; los 10 intactos | Tocaría pruebas con píxeles y coordenadas fijas (`a_pantalla`) |
| Impacto en informe | Agregar subsección a 5.2; lo actual sigue válido | Reescribir medidas y tabla de 5.2 |
| Esfuerzo estimado | 5–7 h | 3–5 h |

## 4. Diseño de la UI

```text
┌────────────┬──────────────────────────────────────┬────────────┐
│ MODO       │                                      │ ACTIVOS 71 │
│ [A][B][B+PSO]                                     │ LLEGADOS 9 │
│ ESCENARIO  │          Canvas 30 × 20 m            │ TIEMPO 12,3│
│ [S1][S2][S3]         origen (0,0) abajo-izq.      │ CRÍTICAS 1 │
│ [▶ Iniciar]│    entrada azul     salida violeta   │ ────────── │
│ [Paso][Reiniciar]                                 │ LEYENDA    │
│ CAPAS      │                                      │ velocidad  │
│ [H][C][R][S]                                      │ densidad   │
└────────────┴──────────────────────────────────────┴────────────┘
```

- **Layout:** tres columnas fijas, todo visible sin menús. Debe caber en 1366×768 para proyector.
- **Atajos visibles en cada botón:** `Espacio` iniciar/pausa, `→` paso, `X` reiniciar, `A`/`B`/`P` modo, `1`/`2`/`3` escenario, `H`/`C`/`R`/`S` capas. Reiniciar usa `X` porque `R` ya es Rutas.
- **Estados:** hover, activo, foco de teclado y deshabilitado; Iniciar es el botón destacado.
- **Estilo:** paneles translúcidos oscuros, recinto claro, `system-ui`. Sin recursos externos.
- **Peatones:** rojo (q=0) → amarillo (0,5) → verde (≥1), igual que pygame.
- **Calor:** misma escala, 0 a 4 personas/m², debajo de paredes y agentes.
- **Grupos (C):** núcleo relleno, frontera hueco, ruido con x gris, cruz en el centro con su tamaño.

### Punto de entrada y reinicio

`python -m modulos.servidor_web` (sin flags) o `python main.py --interfaz` (acepta `--modo`, `--agentes`, `--semilla` como valores iniciales). `python main.py` sin argumentos sigue mostrando ayuda, porque una prueba lo exige.

Al iniciar imprime la URL **primero** y luego intenta abrir el navegador. En WSL usa `explorer.exe` (aquí no hay `wslview` ni `xdg-open`); en otros sistemas, `webbrowser`. Si falla, la URL sigue impresa.

Cambiar modo o escenario interrumpe el episodio y deja uno nuevo en t=0, en pausa, sin cerrar nada.

### B+PSO

El botón queda deshabilitado con el motivo visible, salvo que existan **ambos**: soporte en `main.py` y un `capturas/theta_optimo.json` válido.

**Contrato a acordar con Jheycob:** constante `MODOS = ('A', 'B', 'B+PSO')` en `main.py` y `ejecutar_episodio(n, 'B+PSO', ...)`. JSON con `alpha`, `ks`, `kr` dentro de `LIMITES`. Hoy no existen ni el modo ni el archivo.

### Grupos DBSCAN

`clasificar_puntos(posiciones, eps=1.2, min_samples=5)` se llama una vez por segundo simulado (1,5–1,7 ms de media en S3). El resultado se guarda **por id de agente**, no por índice: entre muestras llegan agentes y la lista se acorta, así que un índice pintaría el tipo en el agente equivocado.

## 5. Revisión de `modulos/entorno.py`

| Verificación | Resultado | Evidencia |
|---|---|---|
| Recinto 30×20 m | Cumple | `mapa.shape == (20, 30)` |
| Origen abajo-izquierda | Cumple | `obtener_celda(0,0) == (0,0)`, `(29.9,19.9) → (19,29)` |
| Bordes superiores excluidos | Cumple | `x=30` e `y=20` → `None` |
| Paso principal 2 m | Cumple | Filas libres 10–11, `y ∈ [10,12)` |
| Paso alternativo 3 m | Cumple | Filas libres 4–6, `y ∈ [4,7)` |
| Barrera | Cumple | Columna 15, 15 celdas |
| `es_transitable` O(1) | Cumple | ~445 ns; indexar mallas de 20 a 2000 cuesta igual (~120 ns) |
| Sin asignaciones por ciclo | **No estrictamente** | `obtener_celda` crea una tupla (`BUILD_TUPLE`) por llamada; no se acumula (pico 744 B en 100 000 llamadas) |

**Hallazgos** (no los corrijo: `AGENTS.md` prohíbe tocar este archivo sin pedido explícito):

- **E1, baja.** La asignación de la tupla no afecta: `es_transitable` solo se usa en el constructor. El motor valida con rectángulos. **Recomendación: no cambiar.**
- **E2, bug real, baja.** `agregar_obstaculo` compara coordenadas exactas (`entorno.py:71`). `agregar_obstaculo(1.2, 11.2)` devuelve `True` y **bloquea la celda de entrada**. Ningún flujo actual lo hace en ejecución y la UI no edita obstáculos.
- **E3, baja.** `30 % 0.1 != 0` por punto flotante, así que `tam_celda=0.1` se rechaza aunque sea válido. El proyecto usa 1.
- **E4, cosmética.** `dibujar_mapa` pinta la salida en naranja y las vistas en vivo en violeta. Conviene aclararlo en el pie de figura.

## 6. Plan de implementación

**Ajustes aprobados por Cris:** trabajo en automático con dos paradas obligatorias (fin del MVP y fin del diseño visual); MVP primero; lanzamiento sin flags con `python -m modulos.servidor_web`; prueba nueva al final de `ejecutar_todas.py`; sin abstracciones extra; explicación para la defensa; sin `git add`, commit ni push; `entorno.py` sin cambios.

**Paso 0. Preparación.** Copiar esta auditoría a `AUDITORIA_UI.md`. Correr la suite como línea base.

### Bloque A: MVP de punta a punta

**Paso 1. `main.py` (cambio exacto para avisar a Jheycob):**
- Firma: agregar `vista=None` al final de `ejecutar_episodio`.
- Creación: si llega `vista`, usarla como `vis` y `reloj`; si no, el flujo actual.
- Tras el `diagnostico.actualizar(dt=0.0)`: `vista.conectar(motor, diagnostico)` si hay vista inyectada.
- Sufijo: `if visualizar or vista is not None`.
- CLI: agregar `--interfaz` al grupo excluyente y una rama con importación diferida de `servidor_web`.
- Correr suite.

**Paso 2. `modulos/servidor_web.py`, sesión:** una clase `SesionWeb`, hilo de simulación, iniciar/pausa/reinicio, cambio de modo y escenario, carpeta temporal, estado JSON, B+PSO deshabilitado con motivo.

**Paso 3. `modulos/servidor_web.py`, HTTP:** `/`, estáticos en lista blanca, `/config`, `/estado`, `/control`, validaciones, puerto y apertura de navegador.
- Los archivos de `web/` se leen **desde disco en cada petición** y se sirven con `Cache-Control: no-store`, para editar CSS y JS y solo recargar el navegador.
- `python -m modulos.servidor_web` lanza la interfaz **sin flags**.
- Para cumplir la regla de prueba autónoma de `AGENTS.md`: `python -m modulos.servidor_web --prueba` corre una comprobación corta y termina.

**Paso 4. `web/` mínimo:** modo, escenario, Iniciar/Pausa, Reiniciar, métricas y canvas con recinto, paredes, entrada, salida y peatones.

**PARADA 1: fin del MVP.** Probar de punta a punta contra el servidor real (HTTP local), correr la suite, indicar a Cris **el comando exacto y la URL exacta** para abrir en Windows, y **esperar su confirmación** antes de seguir.

### Bloque B: mejoras, en este orden

**Paso 5.** Paso a paso y atajos de teclado.

**Paso 6.** Capas Calor (H) y Grupos DBSCAN (C), con `clasificar_puntos` a 1 Hz y resultado guardado por id.

**Paso 7.** Captura PNG del canvas (S).

**Paso 8. Diseño visual** (solo `web/`; objetivo: hermoso y fácil de usar sin explicación):
- **Sistema CSS:** variables en `:root` para paleta oscura con degradado suave, un acento, semáforo, radios, sombras y espaciados. Minimalista.
- **Paneles de vidrio:** fondo translúcido, `backdrop-filter` con blur moderado y borde fino. `@supports not (backdrop-filter: blur(1px))` con fondo semitransparente sólido. El blur no se anima.
- **Botones:** hover, activo, foco y deshabilitado con transiciones cortas; Iniciar con degradado; Modo y Escenario segmentados; atajo en etiqueta pequeña; iconos SVG en línea; motivo de B+PSO visible.
- **Canvas:** calor continuo dibujando la matriz 15×10 en un canvas auxiliar y escalándola con suavizado del navegador (sin `filter` ni blur). Paredes redondeadas; entrada y salida con halo en una capa estática que solo se regenera al redimensionar; peatones con borde fino. Sin `shadowBlur` por cuadro.
- **Responsive:** grid de tres columnas; en pantallas angostas, canvas arriba y paneles debajo. Proporción 30:20 con `ResizeObserver`, HiDPI con `devicePixelRatio` (se recalcula al mover la ventana entre pantallas), tipografía y botones con `clamp()`.
- **Estado:** indicador Listo, Corriendo, Pausado, Terminado, y tarjeta de resumen al terminar (llegados, tiempo).
- **Ligero:** sin imágenes ni recursos externos, solo fuentes del sistema; `web/` completo por debajo de ~40 KB (se mide).
- **Revisión:** 1366×768, 1920×1080 y ventana reducida.

**PARADA 2: fin del diseño visual.** Reportar a Cris y **esperar su confirmación** antes de las pruebas.

**Paso 9. `pruebas/pruebas_interfaz_web.py`** (sin navegador real). En `pruebas/ejecutar_todas.py`, único cambio, al final de la tupla `PRUEBAS`, después de `'pruebas_visualizacion_integrada',`:

```python
    'pruebas_interfaz_web',
```

Cubre:
- Métricas con vista web **idénticas** a las de una corrida por lotes (A y B).
- Pausa no avanza, paso avanza 0,1 s, reinicio y cambio de modo/escenario vuelven a t=0.
- B+PSO rechazado sin requisitos.
- DBSCAN una vez por segundo simulado y tipos correctos por id tras llegadas.
- Solo `127.0.0.1`; `Host` ajeno, JSON ausente y rutas como `../` rechazados.
- `web/` sin URLs externas; `capturas/` sin archivos nuevos.

**Paso 10, opcional y al final.** Capa Rutas (R) con `/estado?rutas=1` a 1 Hz. Se omite si agrega riesgo.

**Paso 11. Cierre:**
- Resumen de cambios y cambios exactos en `main.py` y `ejecutar_todas.py` para Jheycob.
- Guía de prueba en WSL con URL para Windows.
- Capturas para que Wendy documente la sección 5.2.
- Explicación simple para la defensa: conversión de metros (origen abajo-izquierda) a píxeles del canvas, y por qué los pasos de 2 m y 3 m cambian el flujo.

## 7. Verificación final

1. `SDL_VIDEODRIVER=dummy .venv/bin/python -m pruebas.ejecutar_todas` → 11/11.
2. `python main.py --modo B --agentes 40 --visualizar` sigue funcionando.
3. `python -m modulos.servidor_web` y `python main.py --interfaz`, abrir la URL en Windows **con el wifi apagado**, y recorrer modos, escenarios, pausa, paso, reinicio, capas y captura.
4. `git status` no muestra archivos nuevos en `capturas/` por usar la UI. Sin commits ni cambios de rama.

La prueba visual en el navegador de Windows la tendrás que confirmar tú si no puedo operar ese navegador desde esta sesión.

## 8. Registro de implementación

### Bloque A (MVP): COMPLETO — en PARADA 1, esperando confirmación de Cris

Estado: pasos 0 a 4 hechos. Verificado con el servidor real:
- Autoprueba `python -m modulos.servidor_web --prueba`: OK.
- Corrida completa S1 modo B por HTTP: 40/40 llegados, tarjeta de resumen y Reiniciar correctos.
- Windows alcanza el servidor de WSL: `curl.exe` devuelve 200 en `127.0.0.1:8765` y `localhost:8765`.
- Captura real con Edge headless (1366×768) revisada.
- Rechazos: `Host` ajeno 403, `Origin` ajeno 403, sin JSON 415, JSON malo 400, acción desconocida 400, B+PSO 400 con motivo, `/main.py` y `/.git/config` 404.
- Suite: 10/10. `capturas/` sin archivos nuevos por usar la UI.

Archivos nuevos: `modulos/servidor_web.py`, `web/index.html`, `web/estilos.css`, `web/app.js`.
Modificado: `main.py` (15 inserciones, 3 borrados). `pruebas/ejecutar_todas.py` aún sin tocar (paso 9).

### Cambio exacto en `main.py` (para avisar a Jheycob)

1. `ejecutar_episodio(...)` recibe un parámetro nuevo al final: `vista=None`. Los llamadores existentes no cambian.
2. Si llega `vista`, se usa como vista y como reloj (`vis = reloj = vista`). Si no, el flujo anterior (`--visualizar`) queda igual.
3. Después del `diagnostico.actualizar(..., dt=0.0)` inicial: `vista.conectar(motor, diagnostico)` solo si hay `vista`.
4. El sufijo `_visual` de los CSV también se aplica con `vista` (así la UI no sustituye archivos de la batería; además la UI escribe en una carpeta temporal).
5. Argumento nuevo `--interfaz` en el grupo excluyente con `--experimentos` y `--visualizar`; rama `elif args.interfaz:` que importa `modulos.servidor_web` de forma diferida y llama a `servir(...)`.

Para B+PSO, Jheycob solo debe: definir `MODOS = ('A', 'B', 'B+PSO')` en `main.py`, aceptar `'B+PSO'` en `ejecutar_episodio` (hoy lanza `ValueError`) y generar `capturas/theta_optimo.json`. La UI activa el botón sola cuando existen ambos.

### Notas de la implementación
- Una corrida web dura lo mismo que una real a 10 ticks/s: S1 en modo B tarda ~37 s. Si resulta largo para la defensa, se puede añadir un control de velocidad (x1, x2, x4) sin tocar la lógica.
- Primer arranque: los imports (NumPy, scikit-learn) tardan unos segundos antes de imprimir la URL.

### Bloque B (pasos 5 a 8): COMPLETO — en PARADA 2, esperando confirmación de Cris

Cambios sobre el plan pedidos por Cris: control de velocidad x1/x2/x4 y dirección visual sobria (neutros oscuros, un acento plano, canvas pizarra con cuadrícula de 2 m). Esta dirección reemplaza a la del Paso 8 original (sin degradados de acento, sin halos ni iconos).

- **Velocidad:** solo cambia la espera entre ticks en `SesionWeb.tick`; `dt` sigue en 0,1 s. Métricas idénticas a una corrida por lotes en S1 A, S1 B y S2 B, a x2 y x4. Ritmo real medido: x3,97 a x4,00.
- **Fluidez:** el navegador consulta `/estado` 20 veces por segundo e interpola la posición entre dos estados solo al dibujar.
- **Paso a paso:** avanza un tick de 0,1 s y solo funciona en pausa.
- **DBSCAN:** `clasificar_puntos(eps=1.2, min_samples=5)` una vez por segundo simulado, con el resultado guardado por id.
- **Captura:** PNG del canvas descargado por el navegador; no escribe en `capturas/`.
- **Atajos:** Espacio, →, X, V, A, B, P, 1, 2, 3, H, C, S. Espacio siempre es iniciar/pausa, aunque un botón tenga el foco.
- **Verificado con Edge headless:** teclado, capas, resumen final y distribución en 1366×768, 1366×620, 1920×1080, 1100×560 y 900×1000, sin desbordes.
- **Pendiente:** Paso 9 (pruebas automatizadas) y Paso 10 (capa Rutas, opcional). `main.py` no cambió en este bloque.
