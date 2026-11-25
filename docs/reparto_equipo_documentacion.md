# Plan de Trabajo y Reparto de Tareas — Equipo de Documentación (Informe)
**Proyecto:** Simulación de Multitudes y Optimización de Flujo en Entornos Interactivos  
**Materia:** Inteligencia Artificial — Universidad Mayor de San Simón (UMSS)  
**Docente:** Lic. Patricia Rodríguez Bilbao  
**Grupo:** 13  
**Versión:** 3.0 (Entrega Final)

---

## 1. Contexto y Objetivos del Informe Final

El informe escrito representa **10 de los 30 puntos** de la evaluación final de la materia. Para asegurar la máxima calificación, el documento debe presentarse con rigor académico, coherencia metodológica y apego estricto a las observaciones directas realizadas por la docente **Lic. Patricia Rodríguez Bilbao** en sus revisiones.

> **Importante para la Defensa Oral:**  
> Aunque cada integrante tiene secciones asignadas para redactar, auditar y perfeccionar, **todos los integrantes deben comprender la estructura global del documento**. La docente evaluará la coherencia entre los objetivos planteados, la teoría matemática, la ingeniería de software y las conclusiones finales obtenidas.

---

## 2. Normas Editoriales y Observaciones Estrictas de la Docente

Todo texto redactado debe cumplir obligatoriamente las siguientes directrices:

1. **Título Académico de la Docente:**  
   En la carátula, encabezados y cualquier mención institucional debe figurar exclusivamente como:  
   **Lic. Patricia Rodríguez Bilbao** *(bajo ninguna circunstancia utilizar "Ing.")*.
2. **Formato APA 7 Estricto en Tablas y Figuras:**  
   * **El 100 % de las tablas y figuras deben llevar el Título ARRIBA** (ej. *Tabla 5.1-1. Parámetros del motor de agentes* o *Figura 5.4-1. Distribución espacial de clústeres detectados con DBSCAN*).
   * **La Nota / Fuente debe ir SIEMPRE ABAJO** (ej. *Nota. Elaboración propia a partir de los datos registrados por el módulo de telemetría.*).
   * Las tablas deben tener formato de tabla limpia (sin líneas verticales, solo bordes horizontales superior, de encabezado e inferior).
3. **Limpieza Matemática y Tipográfica:**  
   * **Prohibido dejar signos de dólar (`$`) o comandos LaTeX crudos** en el texto del documento final.
   * Todos los símbolos griegos ($\alpha$, $\varepsilon$, $\rho$, $\tau$, $\theta$) deben estar correctamente insertados en formato de texto o mediante el editor de ecuaciones nativo de Word.
4. **Separación Radical de Capítulos (Cero Contaminación Temática):**  
   * **Capítulo III (Marco Teórico):** Solo teoría pura, fundamentos conceptuales y ecuaciones generales. No debe mencionarse Python, módulos `.py`, interfaces, ni parámetros específicos del prototipo.
   * **Capítulo IV (Marco Referencial):** Exclusivamente antecedentes, caso de estudio conceptual ($30 \times 20\text{ m}$ con dos pasos), formulación de la investigación y delimitación del alcance. No debe contener fragmentos de código, tablas de implementación ni configuraciones del algoritmo.
   * **Capítulo V (Ingeniería del Sistema):** Aquí se concentra toda la solución técnica real: arquitectura de los 8 módulos, fórmulas aplicadas a la simulación, parámetros calibrados, experimentos y resultados.

---

## 3. Reparto Equitativo de Capítulos y Secciones

```
+-----------------------------------------------------------------------------------+
|                              EQUIPO DE DOCUMENTACIÓN                              |
+------------------------------+----------------------------------------------------+
| Integrante                   | Capítulos y Secciones Asignadas                     |
+------------------------------+----------------------------------------------------+
| Jhosselin Sthaicy Bustamante | Cap. I (Introducción), Cap. II (Objetivos PAMA)     |
|                              | y Sección 5.1 (Entorno y Agentes)                  |
+------------------------------+----------------------------------------------------+
| Santiago Leonardo Lora Q.    | Cap. IV (Marco Referencial Depurado) y             |
|                              | Sección 5.5 (Diagnóstico de Zonas y Matriz D)      |
+------------------------------+----------------------------------------------------+
| Wendy Choque Aguilar         | Sección 5.2 (Interfaz y Visualización V3) y        |
|                              | Sección 5.3 (Telemetría y Registro en CSV)         |
+------------------------------+----------------------------------------------------+
| Nicole Marisol Flores Ch.    | Cap. III (Marco Teórico Puro),                     |
|                              | Secciones 5.6 a 5.10 (PSO, Pruebas y Resultados),   |
|                              | Cap. VI (Conclusiones) y Cap. VII (Bibliografía)   |
+------------------------------+----------------------------------------------------+
```

---

### Integrante 1: Jhosselin Sthaicy Bustamante Escobar ("Sthaicy")
* **Capítulos y Secciones asignadas:**
  * **I. Introducción:**
    * `1.1. Contexto del problema`: Aglomeraciones humanas, riesgos de avalancha y cuellos de botella en infraestructura crítica (estaciones, recintos feriales, estadios).
    * `1.2. Planteamiento del problema`: Pérdida de eficiencia y atascos en salidas estrechas cuando no existe información sobre rutas alternativas viables.
    * `1.3. Justificación`: Impacto de combinar simulación basada en agentes con IA adaptativa para mitigar acumulación sin requerir infraestructura física adicional.
  * **II. Objetivos:**
    * `2.1. Objetivo General`: Formulación estricta bajo el esquema **PAMA** exigido por la docente:
      * **P (Proceso):** Desarrollar y evaluar un prototipo computacional de simulación bidimensional con navegación adaptativa y detección no supervisada.
      * **A (Actores):** Agentes autónomos peatonales que transitan por un recinto confinado.
      * **M (Medio):** Recinto virtual 2D con un paso principal estrecho y una ruta alternativa amplia.
      * **A (Área):** Inteligencia Artificial aplicada a la optimización de flujos y dinámica de multitudes.
    * `2.2. Objetivos Específicos`: 8 objetivos ordenados y alineados exactamente a los 8 módulos del sistema.
  * **V. Ingeniería — Subsección 5.1: Entorno y Dinámica de Agentes:**
    * Modelo de fuerzas sociales simplificado:
      $$\vec{F}_i = k_o \vec{F}_{\text{objetivo}} + k_s \vec{F}_{\text{separación}} + k_r \vec{F}_{\text{obstáculos}}$$
    * Integración numérica explícita ($\Delta t = 0{,}1\text{ s}$, $v_{\text{deseada}} \in [0{,}9; 1{,}5]\text{ m/s}$, radio peatonal $0{,}25\text{ m}$).
    * Mecanismo de contacto inelástico continuo y barrido de trayectoria para prevenir el 100 % de solapamientos entre agentes y con paredes.

#### Preguntas Clave para la Defensa Oral:
* *¿Cómo se desglosa el esquema PAMA en el objetivo general de su investigación?*
* *¿Por qué el modelo de agentes no utiliza masa explícita y cómo se garantiza que los peatones no se atraviesen en densidades extremas?*

---

### Integrante 2: Santiago Leonardo Lora Quilla ("Santy")
* **Capítulos y Secciones asignadas:**
  * **IV. Marco Referencial (Depuración Estricta):**
    * `4.1. Antecedentes y referentes`: Síntesis de Helbing & Molnár (1995), Reynolds (1987), Treuille et al. (2006) y Fruin (1971).
    * `4.2. Caso de estudio`: Descripción conceptual del recinto geométrico de $30 \times 20\text{ m}$ con muro intermedio, paso principal de 2 m y paso alternativo de 3 m (Figura 4.2-1).
    * `4.3. Formulación de la investigación`: Pregunta de investigación formal e hipótesis sobre la descongestión adaptativa.
    * `4.4. Delimitación del sistema`: Supuestos, alcance y restricciones de la simulación.
    * *Nota de Auditoría:* Eliminar rigurosamente cualquier referencia a nombres de módulos (`.py`), funciones de Python, parámetros de calibración o librerías que hayan quedado rezagadas de versiones previas.
  * **V. Ingeniería — Subsección 5.5: Diagnóstico de Zonas y Congestión:**
    * Justificación y discretización del recinto en celdas de $2 \times 2\text{ m}$ (matriz espacial de $10 \times 15$ celdas útiles).
    * Formulación de la densidad local: $\rho(z, t) = \frac{N(z, t)}{\text{Área Útil}}\ [\text{agentes/m}^2]$.
    * Criterios y reglas de estado:
      * **Libre (0):** $\rho < 1{,}5\text{ ag/m}^2$.
      * **Acumulación (1):** $\rho \ge 1{,}5\text{ ag/m}^2$ con flujo en movimiento.
      * **Congestión Crítica (2):** $\rho \ge 2{,}0\text{ ag/m}^2$ y rapidez media $\bar{v} \le 0{,}5 \bar{v}_{\text{deseada}}$ durante al menos **3 segundos continuos** de persistencia temporal.
    * Construcción de la matriz normalizada de penalización para $A^*$:
      $$D(e, t) = \min\left(1{,}0, \frac{\rho(e, t)}{2{,}0}\right)$$
    * Tablas de umbrales y figuras de estados de zonas (Figura 5.5-1 y 5.5-2) en formato APA 7.

#### Preguntas Clave para la Defensa Oral:
* *¿Por qué una densidad alta no es necesariamente un cuello de botella crítico (diferencia entre estado de acumulación y congestión crítica)?*
* *¿Cómo se calcula el área útil de una celda de $2 \times 2\text{ m}$ cuando un muro cruza parcialmente por ella?*

---

### Integrante 3: Wendy Choque Aguilar ("Wendy")
* **Capítulos y Secciones asignadas:**
  * **V. Ingeniería — Subsección 5.2: Interfaz y Visualización (Versión 3):**
    * Documentación de la nueva interfaz interactiva en `pygame-ce` con panel de control incorporado.
    * Explicación de los botones interactivos en pantalla: selección de modos (A, B, B+PSO), carga de agentes (S1, S2, S3), botones de pausa/reinicio y toggles de información visual.
    * Escala cromática de peatones en función de la razón entre rapidez real y rapidez deseada ($v / v_{\text{deseada}}$): verde brillante para flujo libre hacia rojo intenso para agentes atascados.
    * Representación del mapa de calor continuo de densidad y panel HUD con contadores en tiempo real (activos, llegados, tiempo transcurrido, celdas críticas).
    * Mapeo cartesiano con origen $(0,0)$ en la esquina inferior izquierda.
  * **V. Ingeniería — Subsección 5.3: Telemetría y Registro:**
    * Protocolo de muestreo temporal discreto cada $1{,}0\text{ s}$ simulado.
    * Generación del arreglo matricial no etiquetado $(N_{\text{activos}}, 2)$ con $[x_i(t), y_i(t)]$ en metros, consumido de forma desacoplada por DBSCAN.
    * Fórmulas de cálculo de las métricas agregadas del episodio: tiempo medio de tránsito, tiempo de bloqueo individual ($t_{\text{bloqueo}}$ cuando $\|\vec{v}\| < 0{,}5 v_d$), verificación de solapamientos entre pares de agentes ($d_{ij} < 0{,}50\text{ m}$) y tasa de finalización porcentual.
    * Inclusión de la **Tabla 5.3-1** en formato APA 7 con un fragmento representativo del archivo CSV real de telemetría.

#### Preguntas Clave para la Defensa Oral:
* *¿Cómo garantiza el módulo de telemetría que las posiciones exportadas no contengan información de rutas ni estados internos de los agentes?*
* *¿Qué criterio se aplica en el cálculo del tiempo medio de tránsito para los agentes que no lograron llegar al destino en el horizonte de 180 segundos?*

---

### Integrante 4: Nicole Marisol Flores Choquetopa ("Nicole")
* **Capítulos y Secciones asignadas:**
  * **III. Marco Teórico Puro (3.1 a 3.11):**
    * Redacción matemática y conceptual libre de código:
      * 3.1 Aprendizaje No Supervisado vs. Supervisado.
      * 3.2 Clasificación y Optimización en Inteligencia Artificial.
      * 3.3 Fundamentos del Agrupamiento Espacial (Clustering).
      * 3.4 Algoritmo DBSCAN canónico (Ester et al., 1996): vecindad $\varepsilon$, umbral $\text{MinPts}$, definiciones formales de alcanzabilidad y conectividad por densidad.
      * 3.5 Técnicas complementarias de particionamiento y jerarquía.
      * 3.6 Modelado y simulación basada en agentes (ABM).
      * 3.7 Teoría de densidad, nivel de servicio peatonal y cuellos de botella.
      * 3.8 Planificación de trayectorias con $A^*$ (admisibilidad y consistencia de heurísticas).
      * 3.9 Optimización por Enjambre de Partículas (PSO, Kennedy & Eberhart 1995): ecuaciones de actualización de velocidad y posición de partículas.
      * 3.10 Metodología de evaluación experimental multiescenario.
      * 3.11 Métricas de validación interna de clústeres: Coeficiente de Silueta y Davies-Bouldin.
  * **V. Ingeniería — Subsecciones 5.6 a 5.10 (Integración, PSO y Resultados Finales):**
    * `5.6. Navegación adaptativa y calibración PSO`: Formulación del costo adaptativo $c(e, t) = L(e) [1 + \alpha D(e, t)]$, reglas anti-oscilación ($\tau = 4{,}0\text{ s}$ y margen del $10\%$), formulación de la función multiobjetivo $J(\theta)$, curva de convergencia del enjambre y vector óptimo $\theta^* = [\alpha^*, k_s^*, k_r^*]$.
    * `5.7. Arquitectura e integración del sistema`: Diagrama de componentes, flujo cíclico percepción-diagnóstico-planificación.
    * `5.8. Tecnologías y herramientas empleadas`: Python 3.14, NumPy, scikit-learn, pygame-ce, Matplotlib.
    * `5.9. Pruebas y resultados experimentales definitivos`: Análisis comparativo cuantitativo de los 18 escenarios (S1, S2, S3 con semillas 42, 43, 44) comparando **Modo A vs. Modo B vs. Modo B + PSO**, demostrando la resolución del cuello de botella en S3 semilla 43.
    * `5.10. Limitaciones y trabajo futuro`: Restricciones actuales y posibles extensiones (entornos 3D, agentes heterogéneos con pánico).
  * **VI. Conclusiones Definitivas:**
    * Redacción de las conclusiones concluyentes y definitivas del proyecto, fundamentadas con los datos numéricos obtenidos tras la calibración.
  * **VII. Bibliografía:**
    * Referencias bibliográficas completas en formato APA 7 con sangría francesa y DOIs correspondientes (Russell & Norvig, Helbing & Molnár, Ester et al., Kennedy & Eberhart, Fruin, etc.).

#### Preguntas Clave para la Defensa Oral:
* *¿Por qué la combinación de DBSCAN (no supervisado) y A* (búsqueda informada) constituye un sistema inteligente híbrido y no una simple heurística de control?*
* *¿Qué mejoras concretas aportó la optimización por PSO en comparación con los parámetros fijados manualmente en el Modo B base?*

---

## 4. Guía Rápida de Formateo APA 7 para Tablas y Figuras

Para mantener el 100 % de uniformidad en todo el documento:

### Estructura de una Figura APA 7:
```
Figura 5.4-1
Distribución espacial de clústeres detectados por DBSCAN en S3 (t = 20 s)

[ ... IMAGEN CENTRADA EN ALTA RESOLUCIÓN ... ]

Nota. Los puntos en forma de cruz representan ruido espacial (-1); los símbolos coloreados indican núcleos y fronteras de clústeres de alta densidad. Elaboración propia mediante Python y Matplotlib.
```

### Estructura de una Tabla APA 7:
```
Tabla 5.1-1
Parámetros del motor de agentes y dinámica peatonal

-------------------------------------------------------------------------
Parámetro                  Símbolo      Valor Asignado     Unidad
-------------------------------------------------------------------------
Paso de integración        Δt           0,10               s
Radio peatonal             r            0,25               m
Rango velocidad deseada    v_deseada    [0,9; 1,5]         m/s
Aceleración máxima         a_max        4,00               m/s²
Constante de objetivo      ko           1,00               adimensional
Constante de separación    ks           Calibrado (PSO)    adimensional
Constante de obstáculos    kr           Calibrado (PSO)    adimensional
-------------------------------------------------------------------------
Nota. Elaboración propia a partir del modelo de fuerzas sociales simplificado.
```

---

## 5. Cronograma Crítico de Entregas por Horas y Dependencias (Sábado 21 y Domingo 22)

Para asegurar que el informe esté 100 % consolidado el **domingo por la mañana**, de modo que la **tarde del domingo** se destine a la lectura global, verificación cruzada y preparación de la defensa oral entre los 8 integrantes, se establece la siguiente secuencia coordinada con el avance del equipo de código:

```
+---------------------------------------------------------------------------------------------------------+
| SECUENCIA DE DESBLOQUEO TEMPORAL (DOCUMENTACIÓN)                                                        |
+------------------------------------+--------------------------------------------------------------------+
| Sábado 21, 15:00 (Hito D1)         | Sthaicy entrega Introducción, Objetivos PAMA y Sección 5.1.        |
| Sábado 21, 16:00 (Hito D2)         | Santy entrega Marco Referencial depurado (4.1–4.4) y Sección 5.5.  |
| Sábado 21, 18:30 (Hito D3)         | Wendy entrega Secciones 5.2 (Nueva UI de Cris) y 5.3 (Telemetría). |
| Sábado 21, 21:00 (Hito D4)         | Nicole consolida Capítulo III (Marco Teórico Puro 3.1–3.11).       |
| Domingo 22, 10:30 (Hito D5)        | Nicole integra Resultados V3, Conclusiones y Bibliografía APA 7.   |
| Domingo 22, 11:00–12:30            | Compilación final a DOCX y PDF, verificación de índice y APA 7.    |
| Domingo 22, 14:00–18:00            | REVISIÓN GENERAL Y SIMULACRO DE DEFENSA CON LOS 8 INTEGRANTES.     |
+------------------------------------+--------------------------------------------------------------------+
```

### Detalle de Hitos por Integrante y Dependencia:

| Hito | Fecha y Hora Límite | Integrante | Secciones / Entregables | Dependencia / A Quién Desbloquea |
| :---: | :---: | :---: | :---: | :---: |
| **D1** | **Sábado 21 — 15:00** | **Sthaicy** | • **Cap. I:** Introducción (1.1 a 1.3)<br>• **Cap. II:** Objetivos (2.1 PAMA y 2.2)<br>• **Cap. V:** Sección 5.1 (Entorno y Agentes) | **Independiente:** Entrega los fundamentos del problema y la base física. Permite fijar los objetivos contra los que se medirán las conclusiones. |
| **D2** | **Sábado 21 — 16:00** | **Santy** | • **Cap. IV:** Marco Referencial depurado (4.1 a 4.4, sin código ni parámetros)<br>• **Cap. V:** Sección 5.5 (Diagnóstico de zonas y Matriz D) | **Independiente:** Cumple la observación de depuración de la docente y aporta las tablas y figuras de estados de zonas (Figura 5.5-1 y 5.5-2). |
| **D3** | **Sábado 21 — 18:30** | **Wendy** | • **Cap. V:** Sección 5.2 (Interfaz y Visualización V3 con panel de controles)<br>• **Cap. V:** Sección 5.3 (Telemetría y Registro) | **Depende de Cris (Código C3 a las 16:30):** Wendy recibe las capturas de la nueva interfaz con controles en pantalla y el CSV de telemetría para armar la Tabla 5.3-1 en formato APA 7. |
| **D4** | **Sábado 21 — 21:00** | **Nicole** | • **Cap. III:** Marco Teórico Puro (3.1 a 3.11: DBSCAN, $A^*$, PSO, silueta, etc.) | **Independiente:** Garantiza la base matemática y conceptual sin contaminación de código ni parámetros de implementación. |
| **D5** | **Domingo 22 — 10:30** | **Nicole** | • **Cap. V:** Secciones 5.6 a 5.10 (Navegación PSO, Arquitectura, Resultados 18 escenarios, Limitaciones)<br>• **Cap. VI:** Conclusiones Definitivas<br>• **Cap. VII:** Bibliografía APA 7 | **Depende de Jheycob (Código C4 a las 20:00):** Incorpora la tabla comparativa definitiva (Modo A vs. Modo B vs. Modo B+PSO), los gráficos de convergencia de PSO y la resolución de S3 semilla 43. |
| **D6** | **Domingo 22 — 11:00 a 12:30** | **Todo el Equipo** | • Documento oficial consolidado `informe/2do_Parcial_IA_Corregido.docx`<br>• Exportación y validación de `2do_Parcial_IA_Corregido.pdf` (54+ páginas)<br>• Verificación de numeración correlativa de figuras y tablas APA 7. | **Cierre Documental:** El informe queda terminado e impreso/listo digitalmente antes del almuerzo del domingo. |
