"""Genera Word y LaTeX desde un mismo contenido, sin alterar las evidencias.

Uso: python -m scripts_analisis.corregir_informe
Requiere python-docx únicamente para esta tarea editorial. No modifica requirements.
LaTeX: compilar desde informe/ con pdflatex (dos pasadas) o xelatex.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.image.image import Image
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / 'informe'
NOMBRE = '2do_Parcial_IA_Corregido'
RECURSOS = INFORME / 'recursos_informe'
ORIGINAL = INFORME / '2do PArcial IA.docx'
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'


@dataclass
class Bloque:
    tipo: str
    texto: str = ''
    nivel: int = 0
    numero: str = ''
    filas: list[list[str]] = field(default_factory=list)
    imagen: str = ''
    nota: str = ''


CONTENIDO: list[Bloque] = []


def par(texto, tipo='parrafo'):
    CONTENIDO.append(Bloque(tipo, normalizar(texto)))


def titulo(texto, nivel):
    CONTENIDO.append(Bloque('titulo', texto, nivel))


def tabla(numero, texto, filas, nota='Nota. Elaboración propia con los parámetros y registros del proyecto.'):
    CONTENIDO.append(Bloque('tabla', normalizar(texto), numero=numero,
                           filas=[[normalizar(c) for c in f] for f in filas], nota=nota))


def figura(numero, texto, imagen, nota='Nota. Elaboración propia mediante Python y Matplotlib.'):
    assert (INFORME / imagen).is_file(), imagen
    CONTENIDO.append(Bloque('figura', normalizar(texto), numero=numero, imagen=imagen, nota=normalizar(nota)))


def ecuacion(latex):
    CONTENIDO.append(Bloque('ecuacion', latex))


def normalizar(s):
    s = re.sub(r'\s+', ' ', s).strip()
    cambios = {
        'capturas_dbscan/': 'capturas/',
        '(Hart, Nilsson y Raphael, 1968)': '(Hart et al., 1968)',
        '(Helbing y Molnár, 1995)': '(Helbing & Molnár, 1995)',
        '(Kennedy y Eberhart, 1995)': '(Kennedy & Eberhart, 1995)',
        '(Treuille, Cooper y Popović, 2006)': '(Treuille et al., 2006)',
        '(Rousseeuw, 1987; Davies y Bouldin, 1979)': '(Davies & Bouldin, 1979; Rousseeuw, 1987)',
        'Hart, Nilsson y Raphael (1968)': 'Hart et al. (1968)',
        'Treuille, Cooper y Popović (2006)': 'Treuille et al. (2006)',
        '(scikit-learn, s. f.)': '(scikit-learn developers, s. f.)',
        '; scikit-learn, s. f.)': '; scikit-learn developers, s. f.)',
        '(Reynolds, 1987)': '(Reynolds, 1987)',
        'El resultado del agrupamiento se convierte en una señal para decidir rutas, lo que forma un ciclo de observación y adaptación que se puede verificar y ampliar.':
        'El agrupamiento caracteriza las concentraciones; el diagnóstico calcula por separado la penalización espacial que utiliza A*. El ciclo de observación y adaptación es verificable y ampliable.',
        'se categorizarán con reglas explícitas aplicadas sobre lo que detecta el agrupamiento':
        'se categorizan con reglas explícitas sobre densidad, velocidad y persistencia de los agentes activos',
        'a partir de lo que detecte DBSCAN': 'a partir de la matriz del diagnóstico; DBSCAN describe agrupamientos y ruido',
        'Estas etiquetas surgen de reglas sobre grupos hallados sin etiquetas previas':
        'Estas etiquetas surgen de reglas aplicadas directamente a los agentes activos por celda',
        'promedio de llegada de agentes que completan el recorrido':
        'promedio sobre toda la población, con 180 s asignados a quienes no completan el recorrido',
        'Promedio de llegada de agentes que completan el recorrido':
        'Promedio de tiempos de llegada y penalización de 180 s para los no llegados',
        'python pruebas_telemetria.py': 'python -m pruebas.pruebas_telemetria',
        'pruebas_integracion.py': 'pruebas/pruebas_integracion.py',
        'demo_diagnostico.py': 'demos/demo_diagnostico.py',
        'demo_agentes.py': 'demos/demo_agentes.py',
        'demo_navegacion.py': 'demos/demo_navegacion.py',
        'python-docx para producir los resultados ni este informe':
        'python-docx para producir los resultados experimentales; la edición documental posterior sí utiliza python-docx',
    }
    for a, b in cambios.items():
        s = s.replace(a, b)
    return s


def extraer_imagen(doc, indice, nombre, posicion=0):
    relaciones = doc.paragraphs[indice]._p.xpath('.//a:blip/@r:embed')
    destino = RECURSOS / nombre
    destino.write_bytes(doc.part.rels[relaciones[posicion]].target_part.blob)
    return 'recursos_informe/' + nombre


PRINCIPALES = {
    81: 'I. Introducción', 95: 'II. Objetivos', 107: 'III. Marco teórico',
    161: 'IV. Marco Referencial',
}
SUBTITULOS = {
    82: '1.1. Contexto del problema', 87: '1.2. Planteamiento del problema', 91: '1.3. Justificación',
    96: '2.1. Objetivo general', 98: '2.2. Objetivos específicos',
}


def construir_primera_parte(doc):
    """Conserva I–II y separa los fundamentos de la etapa de ingeniería."""
    for i in range(81, 107):
        if i in PRINCIPALES:
            titulo(PRINCIPALES[i], 1)
        elif i in SUBTITULOS:
            titulo(SUBTITULOS[i], 2)
        elif doc.paragraphs[i].text.strip():
            par(doc.paragraphs[i].text, 'lista' if i in range(99, 107) else 'parrafo')
    construir_marco_teorico()
    construir_marco_referencial(doc)


def construir_marco_teorico():
    """Definiciones y ecuaciones generales, sin describir el software del equipo."""
    titulo('III. Marco teórico', 1)
    titulo('3.1. Aprendizaje no supervisado', 2)
    par('La inteligencia artificial estudia agentes capaces de percibir su ambiente y actuar para alcanzar objetivos. El aprendizaje automático comprende métodos que identifican regularidades a partir de datos. En el aprendizaje no supervisado, las observaciones carecen de etiquetas de respuesta y el propósito consiste en descubrir estructura, agrupaciones o casos atípicos (Russell & Norvig, 2021).')
    par('A diferencia del aprendizaje supervisado, que estima una relación entre entradas y salidas conocidas, el aprendizaje no supervisado utiliza las relaciones internas de los datos. La interpretación de los patrones requiere considerar el significado de las variables y las limitaciones de la medida de similitud.')

    titulo('3.2. Clasificación y optimización', 2)
    par('La clasificación asigna observaciones a categorías conforme a un criterio de decisión. En su modalidad supervisada, las categorías se aprenden a partir de ejemplos etiquetados. El agrupamiento, en cambio, descubre conjuntos por similitud sin disponer de clases de referencia; sus resultados no equivalen por sí solos a categorías semánticas.')
    par('La optimización busca valores de variables de decisión que minimicen o maximicen una función objetivo dentro de un conjunto factible. Las restricciones delimitan las soluciones admisibles. Cuando existen varios criterios, su combinación exige tener en cuenta las unidades, la normalización y la importancia relativa de cada término.')
    ecuacion(r'\min_{\theta\in\Omega} J(\theta)')
    par('En esta expresión, θ es el vector de decisión, Ω el conjunto factible y J la función objetivo.')

    titulo('3.3. Agrupamiento (clustering)', 2)
    par('El agrupamiento organiza observaciones de modo que los miembros de un mismo grupo presenten mayor similitud entre sí que con los de otros grupos. La similitud depende de la representación de los datos y de la distancia escogida. Las diferencias de escala entre variables pueden dominar la distancia si no se consideran adecuadamente.')
    par('Los métodos de partición, como K-Means, requieren fijar el número de grupos. Los métodos basados en densidad identifican regiones pobladas separadas por regiones menos densas y pueden reconocer agrupamientos de forma irregular, sin especificar de antemano su cantidad (Ester et al., 1996).')

    titulo('3.4. DBSCAN', 2)
    par('DBSCAN (Density-Based Spatial Clustering of Applications with Noise) identifica grupos mediante conectividad por densidad. Sus parámetros son ε, radio de vecindad, y MinPts, número mínimo de observaciones en esa vecindad, incluyendo el propio punto (Ester et al., 1996; scikit-learn developers, s. f.).')
    par('Un punto núcleo dispone de al menos MinPts observaciones en su vecindad. Un punto frontera pertenece a la vecindad de un núcleo sin reunir esa cantidad por sí mismo. Los puntos que no se incorporan a ningún grupo se consideran ruido. La expansión de regiones conectadas permite encontrar grupos que no son necesariamente convexos.')
    par('Para observaciones bidimensionales, la distancia euclidiana entre los puntos i y j se expresa como:')
    ecuacion(r'd(i,j)=\sqrt{(x_i-x_j)^2+(y_i-y_j)^2}')
    par('La selección de ε y MinPts influye en la fragmentación de los grupos y en la proporción de ruido. El encadenamiento de puntos cercanos puede unir regiones distintas, y un único radio puede resultar insuficiente cuando coexisten densidades muy diferentes. Un agrupamiento espacial describe proximidad; no demuestra por sí solo una detención o un atasco.')

    titulo('3.5. Técnicas complementarias', 2)
    par('HDBSCAN (Hierarchical DBSCAN) construye una jerarquía de agrupamientos a partir de estimaciones de densidad y permite analizar la estabilidad de los grupos a distintas escalas. Este enfoque es relevante cuando las concentraciones presentan intensidades diferentes (Campello et al., 2013).')
    par('Isolation Forest es un método de detección de anomalías basado en particiones aleatorias. Las observaciones que se aíslan con menos particiones se consideran más atípicas. Una anomalía indica una desviación respecto del conjunto, sin establecer por sí misma su causa ni equivaler necesariamente a una condición problemática (Liu et al., 2008).')

    titulo('3.6. Simulación basada en agentes', 2)
    par('La simulación basada en agentes representa un sistema mediante entidades autónomas que perciben su ambiente e interactúan conforme a reglas de comportamiento. Los patrones colectivos pueden emerger de esas interacciones locales, sin que exista una instrucción central para producirlos (Russell & Norvig, 2021).')
    par('En una representación cinemática continua, la posición y la velocidad describen el movimiento. Una aproximación temporal de primer orden actualiza la posición a partir de la velocidad y de un intervalo de tiempo:')
    ecuacion(r'\vec{p}_i(t+\Delta t)=\vec{p}_i(t)+\vec{v}_i(t)\Delta t')
    par('El modelo de fuerzas sociales interpreta el movimiento peatonal mediante términos que representan la tendencia a alcanzar una velocidad deseada y las interacciones con otros peatones y con el ambiente. Se trata de fuerzas efectivas de comportamiento, distintas de una descripción puramente mecánica de las motivaciones humanas (Helbing & Molnár, 1995).')
    ecuacion(r'm_i\frac{d\vec{v}_i}{dt}=\vec{F}_{i,\mathrm{deseada}}+\sum_j\vec{F}_{ij}+\sum_w\vec{F}_{iw}')
    par('Aquí mᵢ representa la masa o escala de inercia, y los términos de fuerza expresan la relajación hacia el movimiento deseado, las interacciones entre individuos y las interacciones con límites u obstáculos. Otro referente es el modelo de bandadas de Reynolds (1987), basado en separación, alineación y cohesión como reglas locales de movimiento colectivo.')

    titulo('3.7. Densidad, congestión y cuellos de botella', 2)
    par('La densidad espacial es el cociente entre la cantidad de individuos presentes en una región y su área útil. La rapidez media resume los módulos de velocidad de los individuos de esa región:')
    ecuacion(r'\rho(z,t)=\frac{N(z,t)}{A(z)}')
    ecuacion(r'\bar{v}(z,t)=\frac{1}{N(z,t)}\sum_{i\in z}\|\vec{v}_i(t)\|')
    par('N(z, t) es la población de la región z en el instante t y A(z) su área útil. La expresión de rapidez media supone una región no vacía. La densidad se expresa en individuos por unidad de superficie y la rapidez en unidades de longitud por tiempo.')
    par('La congestión supone una restricción del desplazamiento y no se identifica únicamente con la presencia de muchas personas. Un cuello de botella es una reducción de capacidad de paso que puede producir acumulación cuando la demanda supera esa capacidad. La combinación de densidad, velocidad y persistencia temporal aporta una descripción más completa que un conteo aislado.')
    par('Los niveles de servicio peatonal relacionan densidad y condiciones de circulación. Su interpretación depende de la geometría, la actividad y las características de la población; los valores de referencia no constituyen límites universales de seguridad (Fruin, 1971).')

    titulo('3.8. Planificación de rutas con A*', 2)
    par('A* es un algoritmo de búsqueda de caminos en un grafo. Evalúa los nodos mediante la suma del costo acumulado desde el origen y una estimación del costo restante hasta una meta (Hart et al., 1968):')
    ecuacion(r'f(n)=g(n)+h(n)')
    par('g(n) es el costo del recorrido conocido y h(n) la heurística. Una heurística admisible no sobrestima el costo mínimo restante. En búsqueda sobre grafos, la consistencia de la heurística o un tratamiento adecuado de la reapertura de nodos permite conservar las garantías de optimalidad, bajo las condiciones habituales de costos no negativos y existencia de una solución.')
    par('La representación del grafo y la definición de los costos determinan qué significa una ruta de menor costo. La distancia geométrica, el tiempo o una combinación de criterios pueden dar lugar a problemas de búsqueda distintos. A* es una técnica de búsqueda informada, no un algoritmo de aprendizaje no supervisado.')

    titulo('3.9. Optimización con PSO', 2)
    par('PSO (Particle Swarm Optimization) es una metaheurística de optimización inspirada en el comportamiento colectivo. Cada partícula representa una solución candidata y mantiene su posición, su velocidad y la mejor posición que ha encontrado. Su desplazamiento combina inercia, experiencia individual e información compartida por el enjambre (Kennedy & Eberhart, 1995).')
    ecuacion(r'\vec{v}_p^{k+1}=w\vec{v}_p^k+c_1r_1(\vec{b}_p-\vec{x}_p^k)+c_2r_2(\vec{b}_g-\vec{x}_p^k)')
    ecuacion(r'\vec{x}_p^{k+1}=\vec{x}_p^k+\vec{v}_p^{k+1}')
    par('En estas ecuaciones, p identifica la partícula y k la iteración; w es el peso de inercia, c1 y c2 son coeficientes de atracción, r1 y r2 son factores aleatorios, y b_p y b_g representan las mejores posiciones individual y global. La función objetivo permite comparar las soluciones candidatas.')
    par('Una función objetivo con varios criterios puede combinar términos normalizados y una penalización por incumplir restricciones. De forma general:')
    ecuacion(r'J(\theta)=\sum_{\ell=1}^{m}w_{\ell}\widetilde{f}_{\ell}(\theta)+P(\theta)')
    par('Los pesos expresan la importancia relativa de cada criterio, los términos normalizados permiten comparar magnitudes de distintas unidades y P representa penalizaciones. El desempeño de una metaheurística depende del problema, de su parametrización y del presupuesto de evaluación; no implica una garantía general de encontrar el óptimo global.')

    titulo('3.10. Evaluación experimental', 2)
    par('La evaluación experimental compara alternativas bajo condiciones controladas. Para atribuir diferencias a un factor de interés, deben mantenerse comparables las demás condiciones y definirse previamente las variables de respuesta, el criterio de finalización y el tratamiento de observaciones incompletas.')
    par('En procesos estocásticos, las repeticiones con semillas controladas permiten reproducir condiciones iniciales y examinar la variabilidad. Los ensayos emparejados facilitan comparar alternativas sometidas a una misma condición. Los datos destinados a ajustar parámetros deben distinguirse de los utilizados para evaluar su capacidad de generalización.')
    par('Los promedios deben acompañarse de medidas de dispersión y de una descripción del tamaño de muestra. Una mejora descriptiva no constituye por sí sola evidencia de significación estadística. Cuando existe un horizonte de observación, los casos que no alcanzan el objetivo requieren un tratamiento explícito de censura o penalización.')

    titulo('3.11. Calidad del agrupamiento', 2)
    par('La evaluación interna del agrupamiento analiza cohesión y separación sin utilizar etiquetas de referencia. El coeficiente Silhouette compara la disimilitud media de una observación respecto de su propio grupo con la menor disimilitud media respecto de otro grupo (Rousseeuw, 1987):')
    ecuacion(r's(i)=\frac{b(i)-a(i)}{\max(a(i),b(i))}')
    par('a(i) representa la disimilitud dentro del grupo y b(i) la disimilitud respecto del grupo alternativo más próximo. Los valores cercanos a uno indican mejor separación, los cercanos a cero señalan proximidad entre grupos y los negativos sugieren una asignación poco adecuada. Los casos de grupos unitarios o denominadores nulos requieren una convención de cálculo.')
    par('El índice Davies–Bouldin relaciona la dispersión de los grupos con la distancia entre sus centros; valores menores indican una separación relativa más favorable (Davies & Bouldin, 1979). La interpretación de ambos índices exige suficientes grupos válidos y considerar la representación y la distancia utilizadas.')
    par('En agrupamientos basados en densidad debe indicarse el tratamiento del ruido y su proporción. Estos índices describen propiedades geométricas; no determinan el significado de los grupos ni demuestran que correspondan a fenómenos físicos concretos.')


def construir_marco_referencial(doc):
    """Antecedentes, caso, pregunta y alcance; los detalles técnicos quedan en V."""
    titulo('IV. Marco Referencial', 1)
    titulo('4.1. Antecedentes y referentes', 2)
    par('El estudio de las multitudes cuenta con antecedentes que abordan el movimiento individual, las interacciones colectivas y las condiciones de circulación desde enfoques complementarios:')
    par('Helbing y Molnár (1995) describen el movimiento peatonal mediante fuerzas sociales, que representan la tendencia al desplazamiento deseado y las interacciones con otras personas y con los límites del espacio.', 'lista')
    par('Reynolds (1987) muestra que reglas locales de separación, alineación y cohesión permiten explicar patrones de movimiento colectivo en bandadas simuladas.', 'lista')
    par('Treuille et al. (2006) estudian multitudes mediante una representación continua del flujo, vinculando la planificación de desplazamientos con el movimiento del conjunto.', 'lista')
    par('Fruin (1971) relaciona densidad, espacio disponible y condiciones de circulación mediante el concepto de nivel de servicio peatonal.', 'lista')
    par('Estos antecedentes permiten distinguir entre la concentración espacial de individuos, las interacciones que condicionan su movimiento y las restricciones de capacidad del espacio.')

    titulo('4.2. Caso de estudio', 2)
    par('El caso de estudio es un recinto virtual bidimensional con una entrada, una salida común y una barrera intermedia con dos pasos. Uno ofrece un recorrido más directo y estrecho, mientras que el otro constituye una alternativa más larga y ancha. Esta disposición permite examinar la relación entre demanda, capacidad de paso y formación de acumulaciones.')
    par('El escenario es sintético y no representa un edificio concreto. No se emplean datos personales, cámaras ni mediciones de peatones reales. La Figura 4.2-1 delimita conceptualmente el espacio y las dos alternativas de circulación.')
    figura('4.2-1', 'Esquema conceptual del escenario de dos rutas', extraer_imagen(doc, 172, 'escenario_conceptual.png'),
           'Nota. Esquema conceptual del recinto con entrada, salida y dos alternativas de circulación. Elaboración propia; figura conservada del documento original.')

    titulo('4.3. Formulación de la investigación', 2)
    par('Pregunta central. ¿En qué medida el reconocimiento de agrupaciones espaciales y de condiciones persistentes de congestión permite mejorar la circulación frente al seguimiento de recorridos fijos en un entorno virtual de agentes autónomos?')
    par('Hipótesis de trabajo. La consideración de concentraciones persistentes y de alternativas de recorrido puede reducir la espera y redistribuir el flujo respecto de una circulación basada en recorridos fijos, manteniendo controlada la ocupación física. Esta hipótesis expresa una relación por contrastar y no presupone un resultado favorable.')

    titulo('4.4. Delimitación del sistema', 2)
    par('Unidad de análisis: peatones simulados y sus desplazamientos dentro del recinto.', 'lista')
    par('Ámbito espacial: entorno bidimensional, observado en planta, con una entrada, una salida común y obstáculos fijos que generan dos alternativas de paso.', 'lista')
    par('Ámbito temporal: evolución de la circulación durante intervalos de observación delimitados; las detenciones breves se distinguen de las acumulaciones persistentes.', 'lista')
    par('Fenómenos de interés: concentración de individuos, reducción de velocidad, formación de colas y distribución del tránsito entre los pasos.', 'lista')
    par('Alcance: análisis de un caso sintético con fines académicos, sin atribuir sus resultados a una población o infraestructura real.', 'lista')
    par('Fuera de alcance: comportamiento psicológico realista, aprendizaje a partir de videos, predicción de emergencias y certificación de seguridad para infraestructura real.')


def construir_entorno(doc):
    titulo('V. Ingeniería', 1)
    titulo('5.1. Entorno y dinámica de agentes', 2)
    for i in range(240,281):
        texto = doc.paragraphs[i].text.strip()
        if i in (240,247,253,264,271):
            titulo(texto, 3)
        elif i == 265:
            figura('5.1-1', 'Mapa del entorno de simulación de 30 × 20 metros', '../capturas/mapa_escenario.png')
        elif i in (269,270):
            continue
        elif i == 280:
            par('Las pruebas verificaron las dimensiones, índices, obstáculos y conectividad de ambos pasos. Estas comprobaciones topológicas se complementan con las pruebas de movimiento físico y de integración descritas en 5.1.6 y 5.9.')
        elif texto:
            par(texto, 'lista' if i in (244,245,250,251,256,257,258,259,260,261,262,276,277,278) else 'parrafo')
    for k, nombre in enumerate(('pruebas_entorno_original.png', 'pruebas_rutas_original.png')):
        figura(f'5.1-{k+2}', ('Resultados de las pruebas de entorno' if k == 0 else 'Comprobación de conectividad y compatibilidad con A*'),
               extraer_imagen(doc, 286, nombre, k),
               'Nota. Captura de validación conservada del documento original. Los scripts se encuentran actualmente en pruebas/ y se ejecutan mediante python -m pruebas.ejecutar_todas.')
    titulo('5.1.6. Motor de agentes', 3)
    leer_seccion(INFORME / 'Seccion_5_1_agentes.txt', omitir_titulo=True, tabla_def='5.1-1', figura_def='5.1-4',
                 figura_archivo='../capturas/agentes_40_semilla_42.png')
    ecuacion(r'\vec{F}_i=k_o\vec{F}_{\mathrm{objetivo}}+k_s\vec{F}_{\mathrm{separacion}}+k_r\vec{F}_{\mathrm{obstaculos}}')
    ecuacion(r'\vec{p}_i(t+\Delta t)=\vec{p}_i(t)+\vec{v}_i(t+\Delta t)\Delta t')


def leer_seccion(archivo, omitir_titulo=False, tabla_def='', figura_def='', figura_archivo=''):
    """Lee íntegramente las fuentes TXT y transforma tablas/figuras en objetos."""
    lineas = archivo.read_text(encoding='utf-8-sig').splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        i += 1
        if not linea or re.fullmatch(r'-{3,}', linea):
            continue
        if re.match(r'^5\.\d+\s', linea):
            if not omitir_titulo:
                numero, resto = linea.split(' ', 1)
                titulo(numero + '. ' + resto, 2)
            continue
        if linea.startswith('Tabla'):
            m = re.match(r'Tabla\s+(\d+\.\d+-\d+)[.:]\s*(.*)', linea)
            numero, nombre = (m.group(1), m.group(2)) if m else (tabla_def, re.sub(r'^Tabla\s*:\s*', '', linea))
            assert numero, linea
            filas = []
            while i < len(lineas) and not lineas[i].strip(): i += 1
            while i < len(lineas) and ' | ' in lineas[i]:
                filas.append([c.strip() for c in lineas[i].split('|')]); i += 1
            nota = 'Nota. Elaboración propia a partir del código y las evidencias del proyecto.'
            if i < len(lineas) and lineas[i].startswith('Fuente:'):
                nota = 'Nota. ' + lineas[i][7:].strip(); i += 1
            if numero == '5.9-1':
                filas = resultados_tabla()
                nombre = 'Resultados medios de los 18 episodios: tres semillas por escenario y modo'
                nota = 'Nota. Datos de capturas/tabla_comparativa_A_vs_B.csv; redondeo a dos decimales. Solapamientos y cambios son medias de totales por corrida; críticas es la media del máximo simultáneo por corrida. Los conteos fraccionarios provienen del promedio entre semillas.'
            if numero == '5.3-2':
                filas = fragmento_csv()
            tabla(numero, nombre.rstrip('.'), filas, normalizar(nota))
            continue
        if linea.startswith('Figura'):
            m = re.match(r'Figura\s+(\d+\.\d+-\d+)[.:]\s*(.*)', linea)
            numero, nombre = (m.group(1), m.group(2)) if m else (figura_def, re.sub(r'^Figura\s*:\s*', '', linea))
            imagen = re.search(r'Archivo:\s*(capturas/[^.]+\.png)', nombre)
            ruta = '../' + imagen.group(1) if imagen else figura_archivo
            assert numero and ruta, linea
            nombre = re.sub(r'\s*Archivo:.*', '', nombre)
            partes = nombre.split('Fuente:', 1)
            nota = ('Nota. ' + partes[1].strip()) if len(partes) == 2 else 'Nota. Elaboración propia con las evidencias del proyecto.'
            nombre = partes[0].strip().rstrip('.')
            if 'Fuente:' in linea:
                nota = 'Nota. ' + linea.split('Fuente:', 1)[1].strip()
            if numero == '5.5-1':
                nota += ' Demostración cinemática con solapamientos permitidos, independiente del motor físico. Pico de 29,25 agentes/m²; no representa el máximo físico integrado de 4,0 agentes/m².'
            figura(numero, nombre, ruta, nota)
            continue
        if linea.startswith('Fuente:'):
            continue
        if linea in ('Demostración reproducible y fragmento real del CSV', 'Validación'):
            titulo(('5.3.1. ' if linea.startswith('Demostración') else '5.3.2. ') + linea, 3)
            continue
        if linea.startswith('Responsable:'):
            par(linea, 'nota'); continue
        if archivo.name == 'Seccion_5_4.txt':
            linea = linea.replace('motor de agentes (5.1)', 'motor de agentes (5.1.6)')
            linea = linea.replace('no se evaluó con rutas adaptativas', 'esta calibración histórica no evaluó rutas adaptativas; la batería integrada posterior se presenta en 5.9')
            linea = linea.replace('debe revisarse en la integración', 'se interpreta junto con las restricciones de contacto descritas en 5.10')
        if archivo.name == 'Seccion_5_5.txt':
            linea = linea.replace('Tabla 1', 'Tabla 5.5-1')
            if linea.startswith('1. Densidad espacial:'):
                ecuacion(r'\rho(z,t)=\frac{N(z,t)}{A(z)}'); continue
            if linea.startswith('2. Velocidad media local:'):
                ecuacion(r'\bar{v}(z,t)=\frac{1}{N(z,t)}\sum_{i\in z}\|\vec{v}_i(t)\|'); continue
        if archivo.name == 'Seccion_5_6.txt':
            linea = linea.replace('Tabla 1', 'Tabla 5.6-1').replace('(Figura)', '(Figura 5.6-1)')
            linea = linea.replace('que se evaluará en las pruebas de la sección 5.9', 'evaluado por separado en la batería de la sección 5.9')
        if archivo.name == 'Seccion_5_3.txt':
            linea = linea.replace('La integración final deberá conservar', 'La integración final conserva').replace('pasar las listas completas', 'pasa las listas completas').replace('y emplear listas', 'y emplea listas')
        if archivo.name == 'Seccion_5_2.txt' and linea.startswith('La codificación de color'):
            ecuacion(r'v=\sqrt{v_x^2+v_y^2}')
            ecuacion(r'r=\frac{v}{v_{\mathrm{deseada}}}')
            linea=linea.replace('q = hypot(vx, vy) / v_deseada','r').replace('q=0,5','r=0,5').replace('q>=1','r≥1')
        if linea.startswith('[Insertar'):
            continue
        par(linea, 'lista' if linea.startswith('- ') or re.match(r'^\d\. ', linea) else 'parrafo')


def resultados_tabla():
    with (RAIZ / 'capturas/tabla_comparativa_A_vs_B.csv').open(encoding='utf-8', newline='') as f:
        datos = list(csv.DictReader(f))
    encabezado = ['Escenario', 'Agentes', 'Modo', 'Viaje (s)', 'Espera (s)', 'Finalización (%)', 'Solapamientos', 'Críticas máx.', 'Cambios']
    campos = ['tiempo_transito', 'tiempo_espera', 'tasa_finalizacion_pct', 'solapamientos', 'celdas_criticas_max', 'cambios_ruta']
    return [encabezado] + [[d['escenario'], d['n_agentes'], d['modo']] + [f'{float(d[c]):.2f}'.replace('.', ',') for c in campos] for d in datos]


def fragmento_csv():
    with (RAIZ / 'capturas/telemetria_ejemplo.csv').open(encoding='utf-8', newline='') as f:
        lector = csv.DictReader(f); columnas = lector.fieldnames; datos = list(lector)
    seleccion = datos[:3] + [next(d for d in datos if float(d['t']) == 4 and int(d['id']) == 37)]
    return [columnas] + [[str(int(float(d[c]))) if c == 'id' else f'{float(d[c]):.6f}' for c in columnas] for d in seleccion]


def construir_contenido(doc):
    construir_primera_parte(doc)
    construir_entorno(doc)
    leer_seccion(INFORME / 'Seccion_5_2.txt')
    leer_seccion(INFORME / 'Seccion_5_3.txt')
    leer_seccion(INFORME / 'Seccion_5_4.txt')
    leer_seccion(INFORME / 'Seccion_5_5.txt', tabla_def='5.5-1')
    figura('5.5-2', 'Estados de las zonas y densidad en la demostración de diagnóstico', '../capturas/zonas_diagnostico.png',
           'Nota. Evidencia de las reglas de diagnóstico generada por la demostración cinemática; no corresponde a los 18 episodios físicos de la sección 5.9.')
    ecuacion(r'D(e,t)=\min\left(1,\frac{\rho(e,t)}{2{,}0}\right)')
    leer_seccion(INFORME / 'Seccion_5_6.txt', tabla_def='5.6-1', figura_def='5.6-1', figura_archivo='../capturas/comparacion_rutas_A_vs_B.png')
    leer_seccion(INFORME / 'Seccion_5_7_a_5_10.txt')
    titulo('VI. Conclusiones preliminares', 1)
    for texto in [
        'Se implementó un sistema modular que acopla la física a 0,1 s con la observación y el análisis espacial a 1,0 s. DBSCAN caracteriza agrupamientos y ruido, mientras que DiagnosticoCongestion calcula directamente sobre los agentes la matriz D que utiliza A*. La visualización es una vista de lectura y no altera el reloj físico.',
        'En S1 (40 agentes), la finalización media aumentó de 76,67 % en A a 100,00 % en B y el tránsito penalizado descendió de 61,08 a 25,92 s. La mejora agregada dependió especialmente de la semilla 43; con semilla 42 la ruta adaptativa no redujo el tiempo medio. Por tanto, la ventaja no es uniforme en cada corrida.',
        'En S2 (80 agentes), la finalización media pasó de 22,50 % a 100,00 % y la espera media de 132,85 a 4,35 s. Fue el escenario con mayor reducción relativa del tránsito penalizado (78,80 %) en la muestra examinada.',
        'En S3 (120 agentes), la finalización media mejoró de 25,28 % a 86,39 % y el tránsito penalizado pasó de 141,89 a 54,66 s. Persistieron 49 agentes sin llegar en la semilla 43 del modo B; A* mitigó el bloqueo, pero no resolvió todas las restricciones de contacto.',
        'No se observaron solapamientos en los instantes muestreados de los 18 episodios. El máximo de densidad física fue 4,0 agentes/m² y debe distinguirse de los 29,25 agentes/m² de la demostración cinemática. Las tres semillas por escenario permiten conclusiones descriptivas, sin acreditar significación estadística ni validez para evacuaciones reales.',
        'La calibración PSO sobre episodios completos permanece pendiente. El siguiente avance debe conectar evaluar(theta) con el motor, mantener métricas y línea base consistentes, separar semillas de calibración y evaluación y ampliar los análisis de sensibilidad. También requiere revisar la resolución de contactos y el rendimiento de la interfaz antes de generalizar los resultados.',
    ]: par(texto)
    titulo('VII. Bibliografía', 1)
    referencias = [p.text.strip() for p in doc.paragraphs[517:] if re.match(r'^[A-Zs][\w-]+,|^scikit-learn developers', p.text)]
    referencias = [r.replace('https://www.aaai.org/Papers/KDD/1996/KDD96-037.pdf', 'https://cdn.aaai.org/KDD/1996/KDD96-037.pdf') for r in referencias]
    referencias = [r.replace('En Advances in Knowledge Discovery and Data Mining (pp. 160–172). Springer.',
        'En J. Pei, V. S. Tseng, L. Cao, H. Motoda y G. Xu (Eds.), Advances in knowledge discovery and data mining (pp. 160–172). Springer.') for r in referencias]
    referencias.append('Russell, S., & Norvig, P. (2021). Inteligencia Artificial: Un enfoque moderno (4.ª ed.). Pearson.')
    referencias = sorted(set(referencias), key=lambda s: unicodedata.normalize('NFKD', s).casefold())
    for ref in referencias:
        par(ref, 'referencia')


# Fórmulas en línea: mismos tokens matemáticos en Word (OMML) y LaTeX.
INLINE = {
    'f(n) = g(n) + h(n)': r'f(n)=g(n)+h(n)',
    'c(e, t) = L(e)·[1 + α·D(e, t)]': r'c(e,t)=L(e)[1+\alpha D(e,t)]',
    'D(e, t) = mín(1; densidad/2,0)': r'D(e,t)=\min(1,\rho(e,t)/2{,}0)',
    'D(e, t) = mín(1; densidad / 2,0)': r'D(e,t)=\min(1,\rho(e,t)/2{,}0)',
    'D = mín[1; densidad / 2,0]': r'D=\min(1,\rho/2{,}0)',
    'θ = [α, kₛ, kᵣ]': r'\theta=[\alpha,k_s,k_r]',
    'θ = [α, k_s, k_r]': r'\theta=[\alpha,k_s,k_r]',
    'θ = [α, ks, kr]': r'\theta=[\alpha,k_s,k_r]',
    'theta=[alpha, ks, kr]': r'\theta=[\alpha,k_s,k_r]',
    'theta = [alpha, ks, kr]': r'\theta=[\alpha,k_s,k_r]',
    'Xᵢ(t) = [xᵢ(t), yᵢ(t)]': r'X_i(t)=[x_i(t),y_i(t)]',
    'q = hypot(vx, vy) / v_deseada': r'q=\frac{\sqrt{v_x^2+v_y^2}}{v_{\mathrm{deseada}}}',
    'hypot(vx, vy) < 0,5 * v_deseada': r'\sqrt{v_x^2+v_y^2}<0{,}5v_{\mathrm{deseada}}',
    'd_ij < radio_i + radio_j': r'd_{ij}<r_i+r_j',
    'A(z) = 4,0 m²': r'A(z)=4{,}0\,\mathrm{m}^2',
    'Δt = 1,0 s': r'\Delta t=1{,}0\,\mathrm{s}',
    'v̄ ≤ 50 % de v_deseada': r'\bar{v}\le0{,}5\bar{v}_{\mathrm{deseada}}',
    'mín(1; densidad / 2,0)': r'\min(1,\rho/2{,}0)',
}
INLINE_RE = re.compile('|'.join(re.escape(k) for k in sorted(INLINE, key=len, reverse=True)))


def partes_inline(texto):
    fin = 0
    for m in INLINE_RE.finditer(texto):
        if m.start() > fin: yield False, texto[fin:m.start()]
        yield True, INLINE[m.group()]
        fin = m.end()
    if fin < len(texto): yield False, texto[fin:]


class MathOMML:
    """Subconjunto de LaTeX usado en el informe: fracciones, raíces e índices."""
    SIMBOLOS = {'alpha':'α', 'tau':'τ', 'rho':'ρ', 'theta':'θ', 'lambda':'λ', 'Omega':'Ω', 'ell':'ℓ',
                'Delta':'Δ', 'sum':'∑', 'in':'∈', 'le':'≤', 'ge':'≥',
                'cdot':'·', 'times':'×', 'longrightarrow':'→', 'varepsilon':'ε',
                'min':'min', 'max':'max', 'quad':'  ', ',':' ', '|':'‖'}

    def __init__(self, texto): self.s, self.i = texto, 0

    @staticmethod
    def elemento(nombre, hijos=()):
        e = OxmlElement('m:' + nombre)
        for h in hijos: e.append(h)
        return e

    @classmethod
    def run(cls, texto):
        r = cls.elemento('r'); pr = cls.elemento('rPr')
        normal = cls.elemento('nor'); pr.append(normal); r.append(pr)
        t = cls.elemento('t'); t.text = texto; r.append(t)
        return r

    def grupo(self):
        if self.i < len(self.s) and self.s[self.i] == '{':
            self.i += 1; return self.secuencia('}')
        return [self.atomo()]

    def atomo(self):
        c = self.s[self.i]; self.i += 1
        if c == '{':
            return self.elemento('box', [self.elemento('e', self.secuencia('}'))])
        if c != '\\': return self.run(c)
        m = re.match(r'[A-Za-z]+|.', self.s[self.i:])
        cmd = m.group(); self.i += len(cmd)
        if cmd in ('left', 'right'): return self.atomo()
        if cmd in ('mathrm', 'text', 'operatorname'): return self.elemento('box', [self.elemento('e', self.grupo())])
        if cmd == 'frac':
            return self.elemento('f', [self.elemento('num', self.grupo()), self.elemento('den', self.grupo())])
        if cmd == 'sqrt':
            pr = self.elemento('radPr'); h = self.elemento('degHide'); h.set(qn('m:val'), '1'); pr.append(h)
            return self.elemento('rad', [pr, self.elemento('deg'), self.elemento('e', self.grupo())])
        if cmd in ('vec','bar','widetilde'):
            pr = self.elemento('accPr'); ch = self.elemento('chr'); ch.set(qn('m:val'), {'vec':'⃗','bar':'̅','widetilde':'̃'}[cmd]); pr.append(ch)
            return self.elemento('acc', [pr, self.elemento('e', self.grupo())])
        return self.run(self.SIMBOLOS.get(cmd, cmd))

    def secuencia(self, cierre=''):
        nodos = []
        while self.i < len(self.s):
            if cierre and self.s[self.i] == cierre:
                self.i += 1; break
            base = self.atomo(); indices = {}
            while self.i < len(self.s) and self.s[self.i] in '_^':
                tipo = self.s[self.i]; self.i += 1; indices[tipo] = self.grupo()
            if indices:
                nombre = 'sSubSup' if len(indices) == 2 else ('sSub' if '_' in indices else 'sSup')
                hijos = [self.elemento('e', [base])]
                if '_' in indices: hijos.append(self.elemento('sub', indices['_']))
                if '^' in indices: hijos.append(self.elemento('sup', indices['^']))
                base = self.elemento(nombre, hijos)
            nodos.append(base)
        return nodos

    def convertir(self): return self.elemento('oMath', self.secuencia())


def agregar_runs(p, texto, negrita=False, cursiva=False):
    for es_math, parte in partes_inline(texto):
        if es_math: p._p.append(MathOMML(parte).convertir())
        else:
            r = p.add_run(parte); r.bold = negrita; r.italic = cursiva


REF_CURSIVAS = (
    'Advances in knowledge discovery and data mining',
    'IEEE Transactions on Pattern Analysis and Machine Intelligence, PAMI-1',
    'Proceedings of the Second International Conference on Knowledge Discovery and Data Mining',
    'Highway Research Record, 355',
    'IEEE Transactions on Systems Science and Cybernetics, 4',
    "Proceedings of ICNN'95 – International Conference on Neural Networks",
    '2008 Eighth IEEE International Conference on Data Mining',
    'Physical Review E, 51',
    'ACM SIGGRAPH Computer Graphics, 21',
    'Journal of Computational and Applied Mathematics, 20',
    'Inteligencia Artificial: Un enfoque moderno',
    'DBSCAN',
    'ACM Transactions on Graphics, 25',
)


def partes_referencia(s):
    for patron in REF_CURSIVAS:
        if patron in s:
            antes, despues=s.split(patron,1)
            return [(False,antes),(True,patron),(False,despues)]
    return [(False,s)]


def configurar_word(doc):
    s = doc.sections[0]
    s.page_width = Inches(8.5); s.page_height = Inches(11)
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Cm(2.54)
    s.header_distance = s.footer_distance = Cm(1.27)
    for nombre in ('Normal', 'Body Text', 'Heading 1', 'Heading 2', 'Heading 3', 'Caption', 'List Paragraph'):
        estilo = doc.styles[nombre]
        estilo.font.name = 'Times New Roman'; estilo.font.size = Pt(12); estilo.font.color.rgb = RGBColor(0,0,0)
        fuentes=estilo._element.get_or_add_rPr().rFonts
        for attr in list(fuentes.attrib):
            if attr.endswith('Theme'): del fuentes.attrib[attr]
        fuentes.set(qn('w:eastAsia'), 'Times New Roman')
        fuentes.set(qn('w:cs'), 'Times New Roman')
        pf = estilo.paragraph_format; pf.line_spacing = 1.5; pf.space_after = Pt(6); pf.space_before = Pt(0)
        pf.first_line_indent = Cm(1.27); pf.widow_control = True
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for nivel in (1,2,3):
        e = doc.styles[f'Heading {nivel}']; e.font.bold = True; e.font.italic = nivel == 3
        pf=e.paragraph_format; pf.first_line_indent=Cm(0); pf.space_before=Pt(12); pf.space_after=Pt(6)
        pf.keep_with_next = True; pf.alignment = WD_ALIGN_PARAGRAPH.CENTER if nivel == 1 else WD_ALIGN_PARAGRAPH.LEFT
        pf.page_break_before = nivel == 1
    for nombre in ('Caption', 'List Paragraph'):
        doc.styles[nombre].paragraph_format.first_line_indent = Cm(0)
    # Estilos separados para tablas/notas, sin cambiar la tipografía uniforme.
    for nombre in ('Nota APA', 'Celda APA', 'Referencia APA', 'Titulo APA'):
        if nombre not in doc.styles: doc.styles.add_style(nombre, 1)
        e=doc.styles[nombre]; e.base_style=doc.styles['Normal']; e.font.name='Times New Roman'; e.font.size=Pt(12)
        e.paragraph_format.first_line_indent=Cm(0)
    doc.styles['Nota APA'].font.italic=True
    doc.styles['Celda APA'].paragraph_format.line_spacing=1.0
    doc.styles['Celda APA'].paragraph_format.space_after=Pt(3)
    doc.styles['Celda APA'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    doc.styles['Referencia APA'].paragraph_format.left_indent=Cm(1.27)
    doc.styles['Referencia APA'].paragraph_format.first_line_indent=Cm(-1.27)
    doc.styles['Titulo APA'].paragraph_format.keep_with_next=True
    doc.styles['Titulo APA'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    for nombre in ('Header','Footer'):
        doc.styles[nombre].font.name='Times New Roman';doc.styles[nombre].font.size=Pt(12)
    settings = doc.settings.element
    update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');settings.append(update)
    # Numeración de página superior derecha, también en la portada.
    p=s.header.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.first_line_indent=Cm(0)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');p._p.append(field)


def portada_word(doc, fuente, logos):
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0)
    p.paragraph_format.line_spacing=1.0;p.paragraph_format.space_after=Pt(6)
    p.add_run().add_picture(str(INFORME / logos[0]), height=Cm(2.2))
    p.add_run('                 ')
    p.add_run().add_picture(str(INFORME / logos[1]), height=Cm(2.2))
    lineas=[('UNIVERSIDAD MAYOR DE SAN SIMÓN',True),('FACULTAD DE CIENCIAS Y TECNOLOGÍA',True),('INGENIERÍA EN SISTEMAS',True),
            ('SIMULACIÓN DE MULTITUDES Y OPTIMIZACIÓN DE FLUJO EN ENTORNOS INTERACTIVOS: Detección no supervisada de cuellos de botella y optimización metaheurística del flujo',True),
            ('Área: Aprendizaje no supervisado',False),('Subárea: Clasificación y optimización',False),('Materia: Inteligencia Artificial',False),
            ('Docente: Lic. Patricia Rodríguez Bilbao',False),('Carrera: Ing. de Sistemas',False),('Grupo: 13',True),('Integrantes:',True)]
    lineas += [(fuente.paragraphs[i].text,False) for i in range(24,32)]
    lineas += [('Fecha: 17 de Noviembre del 2026',False),('COCHABAMBA - BOLIVIA',False)]
    for texto,bold in lineas:
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0)
        p.paragraph_format.line_spacing=1.0;p.paragraph_format.space_after=Pt(4 if len(texto)<100 else 10)
        p.add_run(texto).bold=bold
    doc.add_page_break()
    p=doc.add_paragraph('Índice');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0);p.runs[0].bold=True
    # Índice estático con hipervínculos: visible sin actualizar campos. Word agrega
    # los números de página mediante COM, si está instalado.
    for k,b in enumerate(CONTENIDO):
        if b.tipo!='titulo' or b.nivel>2: continue
        p=doc.add_paragraph();p.paragraph_format.first_line_indent=Cm(0)
        p.paragraph_format.left_indent=Cm(0 if b.nivel==1 else .6)
        p.paragraph_format.line_spacing=1.0;p.paragraph_format.space_after=Pt(2)
        link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),f'sec_{k}')
        r=OxmlElement('w:r');t=OxmlElement('w:t');t.text=b.texto;r.append(t);link.append(r);p._p.append(link)
        p.add_run('\t')
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),f'PAGEREF sec_{k} \\h')
        rr=OxmlElement('w:r');tt=OxmlElement('w:t');tt.text='';rr.append(tt);f.append(rr);p._p.append(f)


def cap_word(doc, clase, b):
    p=doc.add_paragraph(style='Titulo APA');agregar_runs(p,clase+' '+b.numero,negrita=True)
    p.paragraph_format.space_after=Pt(0)
    p=doc.add_paragraph(style='Titulo APA');agregar_runs(p,b.texto,cursiva=True)


def render_word(fuente, logos):
    doc=Document();configurar_word(doc);portada_word(doc,fuente,logos)
    for k,b in enumerate(CONTENIDO):
        if b.tipo=='titulo':
            p=doc.add_paragraph(b.texto, style=f'Heading {b.nivel}')
            a=OxmlElement('w:bookmarkStart');a.set(qn('w:id'),str(k));a.set(qn('w:name'),f'sec_{k}')
            z=OxmlElement('w:bookmarkEnd');z.set(qn('w:id'),str(k));p._p.insert(0,a);p._p.append(z)
        elif b.tipo=='ecuacion':
            p=doc.add_paragraph();p.paragraph_format.first_line_indent=Cm(0);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p._p.append(MathOMML(b.texto).convertir())
        elif b.tipo in ('parrafo','lista','nota','referencia'):
            estilo={'parrafo':'Normal','lista':'List Paragraph','nota':'Nota APA','referencia':'Referencia APA'}[b.tipo]
            p=doc.add_paragraph(style=estilo)
            if b.tipo=='referencia':
                for cursiva,parte in partes_referencia(b.texto): agregar_runs(p,parte,cursiva=cursiva)
            else: agregar_runs(p,b.texto)
        elif b.tipo=='figura':
            cap_word(doc,'Figura',b)
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0)
            p.paragraph_format.keep_with_next=True
            ruta=INFORME/b.imagen
            im=Image.from_file(str(ruta));ancho,alto=im.px_width,im.px_height
            max_w,max_h=15.8,13.5
            ancho_cm=min(max_w,max_h*ancho/alto)
            p.add_run().add_picture(str(ruta),width=Cm(ancho_cm))
            doc.add_paragraph(b.nota,style='Nota APA')
        elif b.tipo=='tabla':
            apaisada=b.numero in ('5.3-2','5.9-1')
            if apaisada:
                s=doc.add_section(WD_SECTION_START.NEW_PAGE);s.orientation=WD_ORIENT.LANDSCAPE
                s.page_width=Inches(11);s.page_height=Inches(8.5)
            cap_word(doc,'Tabla',b)
            t=doc.add_table(rows=0,cols=len(b.filas[0]));t.alignment=WD_TABLE_ALIGNMENT.CENTER
            pr=t._tbl.tblPr;bordes=OxmlElement('w:tblBorders')
            for borde in ('top','left','bottom','right','insideH','insideV'):
                e=OxmlElement('w:'+borde);e.set(qn('w:val'),'single' if borde in ('top','bottom') else 'nil')
                e.set(qn('w:sz'),'6');bordes.append(e)
            pr.append(bordes)
            anchos=anchos_tabla(b)
            t.autofit=False
            for j,col in enumerate(t.columns): col.width=Cm(anchos[j])
            for i,fila in enumerate(b.filas):
                r=t.add_row()
                trpr=r._tr.get_or_add_trPr();ns=OxmlElement('w:cantSplit');trpr.append(ns)
                if i==0: trpr.append(OxmlElement('w:tblHeader'))
                for j,texto in enumerate(fila):
                    c=r.cells[j];c.width=Cm(anchos[j]);p=c.paragraphs[0];p.style=doc.styles['Celda APA']
                    agregar_runs(p,texto,negrita=i==0)
                    # Evita cortes de tablas pequeñas; tablas grandes pueden continuar
                    # con encabezados repetidos en la página siguiente.
                    p.paragraph_format.keep_with_next=i<len(b.filas)-1 and len(b.filas)<=12
                    if i==0:
                        cb=OxmlElement('w:tcBorders');e=OxmlElement('w:bottom');e.set(qn('w:val'),'single');e.set(qn('w:sz'),'6');cb.append(e);c._tc.get_or_add_tcPr().append(cb)
            doc.add_paragraph(b.nota,style='Nota APA')
            if apaisada:
                s=doc.add_section(WD_SECTION_START.NEW_PAGE);s.orientation=WD_ORIENT.PORTRAIT
                s.page_width=Inches(8.5);s.page_height=Inches(11)
    doc.core_properties.title='Simulación de multitudes y optimización de flujo en entornos interactivos'
    doc.core_properties.author='Grupo 13 — UMSS, Inteligencia Artificial'
    doc.core_properties.subject='Segundo parcial: informe corregido con evidencias del repositorio'
    salida=INFORME/(NOMBRE+'.docx');doc.save(salida)
    return salida


def anchos_tabla(b):
    n=len(b.filas[0]);total=16.5
    if b.numero=='5.3-2': return [2.2,1.0,2.65,2.65,2.65,2.65,5.0,3.8]
    if b.numero=='5.9-1': return [2.3,2.0,1.5,2.4,2.4,2.9,3.2,3.2,2.8]
    if n==7:return [1.5]+[2.5]*6
    if n==3:return [3.5,4.2,total-7.7]
    return [total/n]*n


TEX_CHARS={'&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}',
           '~':r'\textasciitilde{}','^':r'\textasciicircum{}','\\':r'\textbackslash{}',
           '²':r'\ensuremath{^2}','³':r'\ensuremath{^3}','×':r'\ensuremath{\times}',
           '→':r'\ensuremath{\rightarrow}','≥':r'\ensuremath{\ge}','≤':r'\ensuremath{\le}',
           '−':'-','‖':r'\ensuremath{\|}','α':r'\ensuremath{\alpha}','τ':r'\ensuremath{\tau}',
           'θ':r'\ensuremath{\theta}','ρ':r'\ensuremath{\rho}','ε':r'\ensuremath{\varepsilon}',
           'λ':r'\ensuremath{\lambda}','Δ':r'\ensuremath{\Delta}','Σ':r'\ensuremath{\sum}','Ω':r'\ensuremath{\Omega}',
           'ᵢ':r'\ensuremath{_i}','ⱼ':r'\ensuremath{_j}','ₓ':r'\ensuremath{_x}','ᵧ':r'\ensuremath{_y}',
           'ₛ':r'\ensuremath{_s}','ᵣ':r'\ensuremath{_r}','ₒ':r'\ensuremath{_o}',
           '₀':r'\ensuremath{_0}','·':r'\ensuremath{\cdot}','∞':r'\ensuremath{\infty}',
           '∈':r'\ensuremath{\in}','…':r'\ldots{}','̄':'','̅':''}


def escapar_tex(s):
    # Permite cortes de identificadores y rutas sin reducir el tamaño de letra.
    def literal(x):
        x=x.replace('v̄', 'velocidad media')
        return ''.join(TEX_CHARS.get(c,c) for c in x)
    return ''.join('$'+v+'$' if m else literal(v) for m,v in partes_inline(s))


def texto_tex(s):
    """URLs como hipervínculos; el resto admite guiones de corte en rutas."""
    partes=re.split(r'(https?://\S+)',s)
    return ''.join(r'\url{'+p+'}' if p.startswith(('http://','https://')) else escapar_tex(p) for p in partes)


PREAMBULO = r'''\documentclass[12pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage[margin=2.54cm]{geometry}
\usepackage{times}
\usepackage{setspace}
\onehalfspacing
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{float}
\usepackage{hyperref}
\usepackage{array,longtable,ragged2e}
\usepackage{titlesec}
\usepackage{pdflscape}
\hypersetup{hidelinks,pdftitle={Simulación de multitudes y optimización de flujo},pdfauthor={Grupo 13, UMSS}}
\setlength{\parindent}{1.27cm}
\setlength{\parskip}{6pt}
\setlength{\tabcolsep}{3pt}
\setlength{\emergencystretch}{3em}
\setcounter{tocdepth}{2}
\setcounter{secnumdepth}{0}
\titleformat{\section}{\centering\normalsize\bfseries}{}{0pt}{}
\titleformat{\subsection}{\normalsize\bfseries}{}{0pt}{}
\titleformat{\subsubsection}{\normalsize\bfseries\itshape}{}{0pt}{}
\newcolumntype{P}[1]{>{\RaggedRight\arraybackslash}p{#1}}
\begin{document}
'''


def render_tex(fuente,logos):
    lineas=[PREAMBULO,r'\begin{titlepage}\centering\setstretch{1.0}',
            r'\includegraphics[height=2.2cm]{'+logos[0]+r'}\hspace{3cm}\includegraphics[height=2.2cm]{'+logos[1]+'}',
            r'\par\medskip\textbf{UNIVERSIDAD MAYOR DE SAN SIMÓN}\par',
            r'\textbf{FACULTAD DE CIENCIAS Y TECNOLOGÍA}\par',r'\textbf{INGENIERÍA EN SISTEMAS}\par\bigskip',
            r'\textbf{SIMULACIÓN DE MULTITUDES Y OPTIMIZACIÓN DE FLUJO EN ENTORNOS INTERACTIVOS: Detección no supervisada de cuellos de botella y optimización metaheurística del flujo}\par\bigskip']
    for s in ('Área: Aprendizaje no supervisado','Subárea: Clasificación y optimización','Materia: Inteligencia Artificial',
              'Docente: Lic. Patricia Rodríguez Bilbao','Carrera: Ing. de Sistemas','Grupo: 13','Integrantes:'):
        lineas.append(escapar_tex(s)+r'\par\smallskip')
    lineas += [escapar_tex(fuente.paragraphs[i].text)+r'\par\smallskip' for i in range(24,32)]
    lineas += [r'\medskip Fecha: 17 de Noviembre del 2026\par',r'COCHABAMBA -- BOLIVIA',r'\end{titlepage}',r'\tableofcontents\clearpage']
    for k,b in enumerate(CONTENIDO):
        if b.tipo=='titulo':
            if b.nivel==1: lineas.append(r'\clearpage')
            cmd={1:'section',2:'subsection',3:'subsubsection'}[b.nivel]
            lineas.append('\\'+cmd+'{'+escapar_tex(b.texto)+'}'+r'\label{sec:'+str(k)+'}')
        elif b.tipo=='ecuacion':
            lineas.extend([r'\begin{equation*}',b.texto,r'\end{equation*}'])
        elif b.tipo=='referencia':
            ref=''.join(r'\textit{'+texto_tex(s)+'}' if italic else texto_tex(s) for italic,s in partes_referencia(b.texto))
            lineas.append(r'{\hangindent=1.27cm\hangafter=1 '+ref+r'\par}')
        elif b.tipo=='nota':
            lineas.append(r'\noindent\textit{'+texto_tex(b.texto)+r'}\par')
        elif b.tipo=='lista':
            lineas.append(r'\noindent '+texto_tex(b.texto)+r'\par')
        elif b.tipo=='parrafo':
            lineas.append(texto_tex(b.texto)+r'\par')
        elif b.tipo=='figura':
            lineas.extend([r'\begin{figure}[H]',r'\noindent\textbf{Figura '+b.numero+r'}\par',
                           r'\noindent\textit{'+texto_tex(b.texto)+r'}\par\smallskip',r'\centering',
                           r'\includegraphics[width=0.96\linewidth,height=13.5cm,keepaspectratio]{'+b.imagen+'}',
                           r'\par\smallskip\justifying\noindent\textit{'+texto_tex(b.nota)+'}',r'\end{figure}'])
        elif b.tipo=='tabla':
            lineas.extend(tabla_tex(b))
    lineas.append(r'\end{document}')
    destino=INFORME/(NOMBRE+'.tex');destino.write_text('\n\n'.join(lineas)+'\n',encoding='utf-8')
    return destino


def tabla_tex(b):
    anchos=anchos_tabla(b);total=sum(anchos)
    # Descarta el espaciado entre columnas al calcular las cajas de texto.
    apaisada=b.numero in ('5.3-2','5.9-1')
    disponible=(22.86 if apaisada else 16.51) - .211*len(anchos)
    columnas=''.join('P{'+f'{a/total*disponible:.3f}'+'cm}' for a in anchos)
    filas=deepcopy(b.filas)
    out=([r'\begin{landscape}'] if apaisada else []) + [r'\noindent\textbf{Tabla '+b.numero+r'}\par',r'\noindent\textit{'+texto_tex(b.texto)+r'}\par',
         r'\begingroup\setstretch{1.0}',r'\begin{longtable}{'+columnas+'}',r'\toprule']
    cab=' & '.join(r'\textbf{'+texto_tex(c)+'}' for c in filas[0])+r' \\'
    out += [cab,r'\midrule',r'\endfirsthead',r'\toprule',cab,r'\midrule',r'\endhead']
    for f in filas[1:]:out.append(' & '.join(texto_tex(c) for c in f)+r' \\')
    out += [r'\bottomrule',r'\end{longtable}\endgroup',r'\noindent\textit{'+texto_tex(b.nota)+r'}\par']
    if apaisada: out.append(r'\end{landscape}')
    return out


def huellas_protegidas():
    archivos=[ORIGINAL,RAIZ/'requirements.txt']
    for carpeta in ('modulos','capturas'):
        archivos.extend(p for p in (RAIZ/carpeta).rglob('*') if p.is_file())
    return {str(p.relative_to(RAIZ)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos}


def validar(docx,tex,antes):
    d=Document(docx);s=tex.read_text(encoding='utf-8')
    texto='\n'.join(p.text for p in d.paragraphs)
    for nombre in PRINCIPALES.values(): assert nombre in texto and nombre in s,nombre
    for nombre in ('V. Ingeniería','VI. Conclusiones preliminares','VII. Bibliografía'):
        assert nombre in texto and nombre in s,nombre
    for i in range(1,11):
        assert any(b.tipo=='titulo' and b.texto.startswith(f'5.{i}. ') for b in CONTENIDO),i
    inicio_iii=next(i for i,b in enumerate(CONTENIDO) if b.texto=='III. Marco teórico')
    inicio_iv=next(i for i,b in enumerate(CONTENIDO) if b.texto=='IV. Marco Referencial')
    inicio_v=next(i for i,b in enumerate(CONTENIDO) if b.texto=='V. Ingeniería')
    teoria=CONTENIDO[inicio_iii+1:inicio_iv]
    referencial=CONTENIDO[inicio_iv+1:inicio_v]
    assert [re.match(r'(3\.\d+)\.',b.texto).group(1) for b in teoria if b.tipo=='titulo']==[f'3.{i}' for i in range(1,12)]
    assert [re.match(r'(4\.\d+)\.',b.texto).group(1) for b in referencial if b.tipo=='titulo']==[f'4.{i}' for i in range(1,5)]
    assert not any(b.tipo=='tabla' for b in teoria+referencial)
    assert [b.numero for b in referencial if b.tipo=='figura']==['4.2-1']
    for b in teoria+referencial:
        assert not re.search(r'prototipo|implementa|pendiente|en este proyecto|modulos/|\.py\b|\bPAMA\b',b.texto,re.I),b.texto
    for patron in (r'Tabla X\b',r'Figura X\b',r'\[Insertar aquí',r'capturas_dbscan/'):
        assert not re.search(patron,texto+s),patron
    for m in re.finditer(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',s): assert (INFORME/m.group(1)).is_file(),m.group(1)
    assert huellas_protegidas()==antes,'Se alteró un archivo protegido'
    assert len(d.tables)==sum(b.tipo=='tabla' for b in CONTENIDO)
    refs=[b.texto for b in CONTENIDO if b.tipo=='referencia']
    assert len(refs)==13,(len(refs),refs)
    datos={'documento_original':str(ORIGINAL.relative_to(RAIZ)), 'bloques_compartidos':len(CONTENIDO),
           'titulos':[b.texto for b in CONTENIDO if b.tipo=='titulo'], 'tablas':len(d.tables),
           'figuras':sum(b.tipo=='figura' for b in CONTENIDO), 'referencias':len(refs),
           'ecuaciones_word':len(d.element.xpath('.//m:oMath')), 'archivos_protegidos_sin_cambios':len(antes),
           'latex_compilador':None,'pdf':None,'validacion':'correcta',
           'marcos_depurados':{'III':'3.1–3.11: teoría y ecuaciones generales','IV':'4.1–4.4; figura 4.2-1; sin tablas de implementación'}}
    return datos


def finalizar_word(docx):
    """Actualiza PAGEREF y exporta PDF con Word oculto, sin tocar el original.

    Es una alternativa de impresión cuando no existe motor TeX. El registro
    identifica expresamente el origen del PDF, sin atribuirlo a una compilación.
    """
    archivo=str(docx).replace("'", "''")
    pdf=str(docx.with_suffix('.pdf')).replace("'", "''")
    script=r'''
$ErrorActionPreference = 'Stop'
$word = $null
$doc = $null
try {
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $word.Options.SaveNormalPrompt = $false
  $doc = $word.Documents.Open('__DOCX__', $false, $false, $false)
  $doc.Repaginate()
  [void]$doc.Fields.Update()
  $doc.Repaginate()
  [void]$doc.Fields.Update()
  $doc.Save()
  $doc.ExportAsFixedFormat('__PDF__', 17)
  $paginas = $doc.ComputeStatistics(2)
  $resumen = @()
  for ($n = 1; $n -le $paginas; $n++) {
    $inicio = $doc.GoTo(1, 1, $n).Start
    if ($n -lt $paginas) { $fin = $doc.GoTo(1, 1, ($n + 1)).Start } else { $fin = $doc.Content.End }
    $rango = $doc.Range($inicio, $fin)
    $resumen += [pscustomobject]@{pagina=$n; caracteres=$rango.Text.Trim().Length; tablas=$rango.Tables.Count; imagenes=$rango.InlineShapes.Count; inicio=$rango.Text.Substring(0,[Math]::Min(90,$rango.Text.Length))}
  }
  [pscustomobject]@{paginas=$paginas; exportador_pdf='Microsoft Word (DOCX); no compilado desde LaTeX'; paginas_detalle=$resumen} | ConvertTo-Json -Depth 5 -Compress
} finally {
  if ($null -ne $doc) { $doc.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
  if ($null -ne $word) { $word.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
'''.replace('__DOCX__',archivo).replace('__PDF__',pdf)
    codificado=base64.b64encode(script.encode('utf-16le')).decode('ascii')
    resultado=subprocess.run(['powershell','-NoProfile','-NonInteractive','-EncodedCommand',codificado],
                             capture_output=True,timeout=240)
    if resultado.returncode:
        raise RuntimeError(resultado.stderr.decode('utf-8',errors='replace'))
    salida=resultado.stdout.decode('utf-8-sig',errors='replace').strip()
    # PowerShell 5.1 usa la página de códigos de consola en procesos redirigidos.
    return json.loads(salida)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finalizar-word',action='store_true',help='Actualizar índice y exportar PDF mediante Word instalado (oculto).')
    args=parser.parse_args()
    RECURSOS.mkdir(exist_ok=True)
    antes=huellas_protegidas()
    doc=Document(ORIGINAL)
    logos=[extraer_imagen(doc,0,'logo_umss.png',0),extraer_imagen(doc,0,'logo_fcyt.png',1)]
    construir_contenido(doc)
    salida_docx=render_word(doc,logos);salida_tex=render_tex(doc,logos)
    comprobacion=validar(salida_docx,salida_tex,antes)
    motor=shutil.which('pdflatex') or shutil.which('xelatex')
    if motor:
        for _ in range(2):
            subprocess.run([motor,'-interaction=nonstopmode','-halt-on-error',salida_tex.name],cwd=INFORME,check=True,capture_output=True)
        comprobacion['latex_compilador']=motor
        comprobacion['pdf']=NOMBRE+'.pdf'
        comprobacion['exportador_pdf']='LaTeX: '+motor
    if args.finalizar_word:
        comprobacion.update(finalizar_word(salida_docx))
        comprobacion['pdf']=NOMBRE+'.pdf'
        # Word solo modifica el archivo derivado y actualiza sus campos.
        assert huellas_protegidas()==antes
        validar(salida_docx,salida_tex,antes)
    comprobacion['referencia_russell']='Se conserva el título en español y el año 2021 solicitados; la fuente oficial consultada corresponde a la cuarta edición en inglés. No se confirmó una edición española con esos datos.'
    (INFORME/'validacion_informe_corregido.json').write_text(json.dumps(comprobacion,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(comprobacion,ensure_ascii=False,indent=2))
    print('Generados:',salida_docx,salida_tex)
    if not motor:print('No hay pdflatex/xelatex disponible; LaTeX preparado para compilar desde informe/.')


if __name__=='__main__':
    main()
