# Interfaz web del simulador

## a) Qué es y cómo ejecutarla

Es una interfaz local para controlar y observar la simulación desde el navegador. Funciona sin internet y no usa recursos externos.

```bash
python -m modulos.servidor_web   # o: python main.py --interfaz
```

Abrir **http://127.0.0.1:8765/**. Si el puerto está ocupado, el programa usa uno de los 10 siguientes e imprime la dirección. `Ctrl+C` lo cierra.

Antes de la defensa deben estar instalados Python, NumPy, scikit-learn, pygame-ce (`requirements.txt`) y un navegador. Sin internet no se puede usar `pip`.

## b) Controles y atajos

Los atajos están ocultos por defecto; se muestran con el botón de teclado o con `?`. También aparecen al pasar el mouse sobre cada botón.

| Control | Atajo | Efecto |
|---|---|---|
| Modo A / B / B+PSO | `A` `B` `P` | Ruta fija, adaptativa o adaptativa calibrada |
| Escenario S1 / S2 / S3 | `1` `2` `3` | 40, 80 o 120 agentes |
| Semilla 42 / 43 / 44 | `Q` `W` `E` | Generación reproducible |
| Iniciar / Pausa | `Espacio` | Corre o detiene el episodio |
| Paso | `→` | Avanza 0,1 s, solo en pausa |
| Reiniciar | `X` | Vuelve a t = 0 en pausa |
| Velocidad x1 / x2 / x4 | `V` | Cambia el ritmo, no la física |
| Calor / Grupos / Rutas | `H` `C` `R` | Densidad, DBSCAN y rutas restantes |
| Capturar | `S` | Descarga un PNG del recinto |
| Tema | `T` | Oscuro o claro |
| Mostrar atajos | `?` | Muestra u oculta las etiquetas |

Cambiar modo, escenario o semilla reinicia el episodio en t = 0 y en pausa.

## c) Arquitectura

- **Python calcula todo:** física, DBSCAN, diagnóstico, rutas y métricas. El navegador solo dibuja y envía órdenes.
- **Hilo de simulación:** `SesionWeb` se pasa como `vista` a `main.ejecutar_episodio`, así la interfaz ejecuta el mismo ciclo que las corridas por lotes. El paso físico sigue en 0,1 s.
- **Endpoints:** `GET /config` (mapa), `GET /estado` (estado actual) y `POST /control` (órdenes). Solo escucha en `127.0.0.1`.
- **Calor:** usa `diagnostico.densidad`, que cambia cada segundo simulado. El navegador mezcla suavemente la matriz anterior y la nueva.
- **Rutas:** se envían solo con la capa activa (`/estado?rutas=1`) y como máximo una vez por segundo simulado.
- Los CSV de las corridas web van a una carpeta temporal; la interfaz no escribe en `capturas/`.

## d) Cambios para Jheycob

**`main.py`:**
1. `ejecutar_episodio(..., visualizar=False, theta=None, vista=None)`; `vista` va al final.
2. Si llega `vista`, se usa como vista y reloj, y se llama `vista.conectar(motor, diagnostico)` tras el diagnóstico inicial.
3. El sufijo `_visual` también se aplica con `vista`.
4. Se agrega `--interfaz` al grupo excluyente, con import diferido de `modulos.servidor_web`.

**`pruebas/ejecutar_todas.py`:** una línea, `'pruebas_interfaz_web',`, al final de `PRUEBAS`.

## e) Pruebas

La suite tiene 13 scripts: `python -m pruebas.ejecutar_todas`. `pruebas_interfaz_web` cubre:

- Métricas de la vista web idénticas a una corrida por lotes (A y B, S1).
- Pausa, paso de 0,1 s, reinicio y cambio de modo, escenario o semilla.
- B_PSO rechazado sin requisitos y aceptado con un theta válido.
- DBSCAN una vez por segundo simulado, con tipos por id tras llegadas.
- Rutas solo a pedido y como máximo una vez por segundo simulado.
- Solo `127.0.0.1`; `Host`, `Origin`, cuerpo sin JSON y rutas `../` rechazados.
- `web/` sin URLs externas y `capturas/` sin archivos nuevos.

## f) Para la defensa

**Metros a píxeles.** El recinto mide 30 × 20 m con origen abajo a la izquierda; el canvas tiene su origen arriba a la izquierda.

```text
escala = ancho_canvas / 30
px = x · escala
py = (20 − y) · escala
```

En un canvas de 900 × 600, la escala es 30 px/m y la entrada (1, 11) cae en (30, 270).

**Por qué el ancho cambia el flujo.** El flujo se aproxima con `Q = densidad · velocidad · ancho`, así que el ancho fija la capacidad: a igual densidad y velocidad, el paso de 3 m admite hasta 1,5 veces lo del paso de 2 m. A densidad alta, los agentes presionan contra la boca del paso y forman un **arco** que lo bloquea. Las rutas adaptativas detectan la congestión y **reparten la carga entre ambos pasos**.

Medias de las semillas 42, 43 y 44 (`capturas/v3/tabla_comparativa_v3.csv`), porcentaje de agentes que llegan:

| Escenario | A | B | B_PSO |
|---|---:|---:|---:|
| S1 (40) | 76,67 | 100,00 | 100,00 |
| S2 (80) | 22,50 | 100,00 | 100,00 |
| S3 (120) | 25,28 | 86,39 | 100,00 |

## g) Estado de B+PSO

- El modo real es `B_PSO`. La interfaz lo muestra como B+PSO y carga theta con `main.cargar_theta`.
- El botón se habilita solo si existe un `capturas/theta_optimo.json` válido. Ese archivo viene en el repositorio (calibración provisional; si el equipo recalibra, se sobrescribe).
- Calibración: S3, semillas 101 y 102, 6 partículas y 4 iteraciones. Resultado: `alpha = 2,984`, `ks = 2,000`, `kr = 0,977`, con `J = 0,1333`.
- En la evaluación final (semillas 42, 43 y 44), B_PSO llegó al 100 % en los 9 episodios. En S3, el viaje medio bajó de 54,66 s (B) a 32,46 s, y la espera de 29,56 s a 2,90 s. En S1 el viaje subió de 25,92 s a 27,01 s.
- **Cómo verificar:** abrir la interfaz; el aviso "B+PSO no disponible" no aparece y el botón responde a clic o `P`.
- Para repetirlo, ver [Cómo habilitar B+PSO](../../AUDITORIA_UI.md#cómo-habilitar-bpso).

## h) Pendientes

- `ks` quedó en su límite superior (2,0): el óptimo podría estar fuera del rango permitido. Son pocas semillas y una calibración corta, no un óptimo garantizado.
- `--experimentos-v3` sobrescribe `capturas/comparacion_experimental_A_vs_B.png`. Por eso la comparación se generó aparte y se guardó en `capturas/v3/`.
- Falta actualizar en el README la mención a diez scripts y a PSO pendiente, y el encabezado "NO integrado" de `modulos/optimizacion_pso.py`.
- Falta la revisión manual en el navegador de la defensa y las capturas de la sección 5.2.
