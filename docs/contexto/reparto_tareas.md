Segundo avance: reparto de tareas (Ingeniería)

Entrega: mañana 17/11, 12:45, informe impreso. Las correcciones de I-IV las hacen todos juntos después. Este reparto cubre solo la sección V (Ingeniería).

Acuerdos de interfaz (leer todos, antes de programar)

Para que el código de cada uno encaje con los demás, estos son los formatos comunes:

Estado de agente: id, x, y, vx, vy, v_deseada, destino, ruta
Telemetría (salida de la 2, entrada de la 3): una fila por agente y por segundo → t, id, x, y, vx, vy, dist_vecino_medio, t_bloqueo
Diagnóstico (salida de la 3, entrada de la 4): matriz de densidad por celda de 2×2 m, con estado libre / acumulación / crítica
Costo de ruta (entrada de A*): D(e,t) = mín(1; densidad/2,0), valor entre 0 y 1
Lenguaje: Python (NumPy, scikit-learn, Pygame, Matplotlib). Entorno: 30 × 20 m, paso principal 2 m, ruta alternativa 3 m, Δt = 0,1 s.
Reparto
1. Alba Zapata Cristhian: Motor del escenario (parte 1: entorno)

Qué hacer: construir el mundo donde viven los agentes.

Recinto de 30×20 m con barrera central, paso principal (2 m) y ruta alternativa (3 m), entrada a la izquierda y salida a la derecha.
Representar el mapa como cuadrícula de celdas (libre/obstáculo) para que A* y la densidad lo usen.
Clase Entorno con funciones: es_transitable(x,y), obtener_celda(x,y), obstaculos().
Soporte para configurar obstáculos y ancho de pasos desde un archivo o parámetros.

Entrega: código del entorno + imagen del mapa + texto para 5.1 (primera mitad).

2. Bustamante Escobar Jhosselin: Motor de agentes (parte 2: movimiento)

Qué hacer: dar vida a los agentes.

Clase Agente con posición, velocidad, radio (0,25 m), velocidad deseada (0,9-1,5 m/s) y destino.
Movimiento por fuerzas simplificadas: atracción al destino + separación de otros agentes + repulsión de paredes. Fórmula: Fi = ko·F_objetivo + ks·F_separación + kr·F_obstáculos.
Limitar velocidad y aceleración máximas; actualizar p(t+Δt) = p(t) + v·Δt.
Generar 40/80/120 agentes en la entrada con semilla aleatoria fija.

Entrega: código + video/capturas de agentes moviéndose + texto para 5.1 (segunda mitad).

3. Choque Aguilar Wendy: Visualización

Qué hacer: que se vea la simulación.

Ventana Pygame: dibujar paredes, agentes (puntos), entrada y salida.
Colorear agentes según velocidad (verde = fluye, rojo = casi detenido).
Mapa de calor de densidad superpuesto y activable con una tecla.
Panel con contadores: agentes activos, llegados, tiempo transcurrido.
Coordinar con 1 y 2 para consumir su código.

Entrega: código + capturas de pantalla (clave para el informe) + texto para 5.2: Interfaz y visualización.

4. Flores Choquetopa Nicole: Telemetría

Qué hacer: registrar lo que pasa para analizarlo.

Cada 1 s guardar por agente: posición, velocidad, distancia media a vecinos cercanos y tiempo acumulado con velocidad menor a 50 % de la deseada.
Exportar a CSV con el formato acordado.
Contar solapamientos (distancia entre centros menor a suma de radios) y agentes que llegan al destino.
Función para entregar los datos de un instante en forma de arreglo NumPy [x, y] (lo que consume DBSCAN).

Entrega: código + fragmento del CSV generado + texto para 5.3: Telemetría y registro.

5. Flores Mamani Daniel: DBSCAN (detección de grupos)

Qué hacer: detectar dónde se juntan los agentes.

Cada 1 s aplicar sklearn.cluster.DBSCAN sobre las posiciones [x, y] con ε = 1,2 m y min_samples = 5.
Devolver etiquetas por agente (−1 = ruido) y el tamaño/centro de cada clúster.
Calibración: probar varios ε (0,8; 1,0; 1,2; 1,5; 2,0) y min_samples (3-8) y registrar en una tabla cuántos clústeres y cuánto ruido da cada combinación. Esa tabla va al informe.
Calcular Silhouette y Davies-Bouldin cuando haya al menos 2 clústeres.

Entrega: código + tabla de calibración + capturas de clústeres coloreados + texto para 5.4: Detección con DBSCAN.

6. Lora Quilla Santiago: Diagnóstico de congestión

Qué hacer: decidir qué zona está realmente congestionada (juntarse no es lo mismo que estar atascado).

Dividir el mapa en celdas de 2×2 m y calcular densidad = agentes / área útil y velocidad promedio por celda.
Clasificar cada celda con reglas:
Libre: densidad < 1,5
Acumulación: densidad ≥ 1,5 sin bloqueo prolongado
Crítica: densidad ≥ 2,0 y velocidad ≤ 50 % de la deseada durante al menos 3 s
Generar la matriz D(e,t) = mín(1; densidad/2,0) para A*.
Verificar que con 120 agentes realmente se llegue a densidad crítica cerca del paso; si no, proponer ajuste (más agentes o paso más estrecho).

Entrega: código + tabla de umbrales + capturas de zonas por estado + texto para 5.5: Diagnóstico de zonas.

7. Orellana Castro Keyla: Navegación adaptativa (A*)

Qué hacer: que los agentes elijan rutas inteligentes.

Implementar A* sobre la cuadrícula con costo c(e,t) = L(e)·[1 + α·D(e,t)] y heurística euclidiana.
Modo A: ruta fija (camino más corto sin considerar congestión). Modo B: recalcular con costo adaptativo.
Reglas anti-oscilación: intervalo mínimo entre recálculos τ (2-6 s) y aceptar la nueva ruta solo si mejora el costo en cierto margen.
Si no hay alternativa viable, mantener la ruta actual.
Si hay tiempo: esbozo de PSO (3 variables: α, ks, kr; función de costo J con tiempo de tránsito, espera y solapamientos).

Entrega: código + comparación visual de rutas A vs B + texto para 5.6: Navegación adaptativa.

8. nicole(tarea de cristian q no pudo hacer): Integración, pruebas y armado del documento

Qué hacer: unir todo y que el informe quede completo.

Crear el programa principal que conecte los módulos: simulación → telemetría → DBSCAN → diagnóstico → A* → de vuelta a la simulación.
Correr los escenarios S1/S2/S3 en modo A y modo B con al menos 3 semillas y armar una tabla preliminar: tiempo medio de viaje, tiempo de espera, tasa de finalización, solapamientos.
Redactar 5.7: Arquitectura e integración (diagrama de capas), 5.8: Tecnologías y herramientas, 5.9: Pruebas y resultados preliminares, 5.10: Limitaciones y trabajo pendiente.
Definir formato común (fuente, interlineado, numeración de figuras y tablas) y armar el documento final, portada, bibliografía e impresión.