import docx
import copy
import os

def actualizar_documento(origen, destino):
    print(f"Cargando {origen}...")
    doc = docx.Document(origen)
    
    # 1. FECHA EN PORTADA (P20)
    print("1. Actualizando fecha en portada...")
    doc.paragraphs[20].text = "                Fecha: 25 de Noviembre del 2026"
    
    # 2. ÍNDICE (P22 a P60)
    print("2. Actualizando índice de contenidos...")
    doc.paragraphs[22].text = "Índice"
    doc.paragraphs[23].text = ""
    
    indice_items = [
        ("1. Introducción", True),
        ("   1.1. Contexto del problema", False),
        ("   1.2. Planteamiento del problema", False),
        ("   1.3. Justificación", False),
        ("2. Objetivos", True),
        ("   2.1. Objetivo general", False),
        ("   2.2. Objetivos específicos", False),
        ("3. Marco teórico", True),
        ("   3.1. Aprendizaje no supervisado", False),
        ("   3.2. Clasificación y optimización", False),
        ("   3.3. Agrupamiento (clustering)", False),
        ("   3.4. DBSCAN", False),
        ("   3.5. Técnicas complementarias", False),
        ("   3.6. Simulación basada en agentes", False),
        ("   3.7. Densidad, congestión y cuellos de botella", False),
        ("   3.8. Planificación de rutas con A*", False),
        ("   3.9. Optimización con PSO", False),
        ("   3.10. Evaluación experimental", False),
        ("   3.11. Calidad del agrupamiento", False),
        ("4. Marco referencial", True),
        ("   4.1. Antecedentes del dominio y problemáticas de circulación", False),
        ("   4.2. Caracterización del escenario de estudio", False),
        ("   4.3. Delimitación del sistema", False),
        ("5. Ingeniería del proyecto", True),
        ("   5.1. Entorno de simulación y motor de agentes", False),
        ("   5.2. Interfaz y visualización interactiva del simulador", False),
        ("   5.3. Telemetría y registro en CSV", False),
        ("   5.4. Detección no supervisada con DBSCAN", False),
        ("   5.5. Diagnóstico de zonas y cuadrícula espacial", False),
        ("   5.6. Navegación adaptativa con A* y calibración PSO", False),
        ("   5.7. Arquitectura modular e integración del ciclo", False),
        ("   5.8. Tecnologías y herramientas", False),
        ("   5.9. Pruebas y resultados experimentales", False),
        ("6. Conclusiones", True),
        ("7. Bibliografía", True),
    ]
    
    for idx, (texto, es_negrita) in enumerate(indice_items):
        p_idx = 24 + idx
        if p_idx <= 60:
            p = doc.paragraphs[p_idx]
            p.text = texto
            if p.runs:
                p.runs[0].bold = es_negrita
    
    # Limpiar cualquier párrafo sobrante del índice anterior (entre 24 + len y 60)
    for p_idx in range(24 + len(indice_items), 61):
        doc.paragraphs[p_idx].text = ""

    # 3. TABLAS EN SECCIÓN 5.5 (DIAGNÓSTICO)
    print("3. Corrigiendo numeración de tablas en sección 5.5...")
    doc.paragraphs[339].text = "Tabla 5.5-1"
    doc.paragraphs[343].text = "Tabla 5.5-2"

    # 4. CALIBRACIÓN PSO EN SECCIÓN 5.6 (P364)
    print("4. Actualizando calibración PSO en sección 5.6...")
    doc.paragraphs[364].text = (
        "Para calibrar la respuesta del algoritmo adaptativo se integró el método de Optimización por "
        "Enjambre de Partículas (PSO; Kennedy & Eberhart, 1995). El optimizador opera sobre el vector de "
        "parámetros θ = (α, ks, kr), donde α modula la sensibilidad frente al costo de congestión D(e, t) "
        "en A*, mientras que ks y kr ajustan las fuerzas de repulsión inter-agente y frente a obstáculos "
        "del motor físico. La calibración evaluó la función de costo multiobjetivo J(θ) minimizando el tiempo "
        "de tránsito, el tiempo de espera y las penalizaciones por agentes no evacuados bajo el escenario "
        "crítico S3. El proceso convergió al vector óptimo θ* = (α = 2,984, ks = 2,000, kr = 0,977), cuyos "
        "parámetros fueron exportados y acoplados directamente al ciclo de simulación y al servidor web "
        "para constituir el modo B+PSO."
    )

    # 5. TABLA 5.9-1 Y DATOS V3
    print("5. Actualizando Tabla 5.9-1 con los 27 episodios V3...")
    doc.paragraphs[395].text = "Resultados medios de los 27 episodios V3: tres semillas por escenario y modo de navegación"
    doc.paragraphs[396].text = (
        "Nota. Datos extraídos de capturas/v3/tabla_comparativa_v3.csv; redondeo a dos decimales. "
        "Solapamientos y cambios son medias de totales por corrida; críticas es la media del máximo simultáneo por corrida. "
        "Se evaluaron tres semillas (42, 43, 44) por cada combinación de escenario y modo. Elaboración propia."
    )

    t = doc.tables[11]
    # Asegurar que la tabla tenga 10 filas (1 header + 9 datos)
    while len(t.rows) < 10:
        t._tbl.append(copy.deepcopy(t.rows[1]._tr))

    datos_v3 = [
        ['S1', '40', 'A', '61,08', '41,34', '76,67', '0,00', '0,33', '0,00'],
        ['S1', '40', 'B', '25,92', '0,89', '100,00', '0,00', '0,00', '110,33'],
        ['S1', '40', 'B+PSO', '27,01', '0,81', '100,00', '0,00', '0,00', '140,00'],
        ['S2', '80', 'A', '143,94', '132,85', '22,50', '0,00', '5,67', '0,00'],
        ['S2', '80', 'B', '30,52', '4,35', '100,00', '0,00', '1,00', '343,67'],
        ['S2', '80', 'B+PSO', '29,20', '1,93', '100,00', '0,00', '0,33', '361,67'],
        ['S3', '120', 'A', '141,89', '130,44', '25,28', '0,00', '8,67', '0,00'],
        ['S3', '120', 'B', '54,66', '29,56', '86,39', '0,00', '3,33', '566,67'],
        ['S3', '120', 'B+PSO', '32,46', '2,90', '100,00', '0,00', '0,00', '657,00'],
    ]

    for i, row in enumerate(datos_v3):
        for j, val in enumerate(row):
            cell = t.rows[i+1].cells[j]
            cell.text = val
            if cell.paragraphs and cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].font.size = docx.shared.Pt(9)

    # 6. ANÁLISIS EXPERIMENTAL EN 5.9 (P398 - P402, P408)
    print("6. Actualizando análisis de resultados en sección 5.9...")
    doc.paragraphs[398].text = (
        "En S1 (40 agentes), el modo estático A completó una media de 76,67 % con un tiempo de viaje de 61,08 s "
        "debido al atasco en la semilla 43. Tanto el modo B como el modo B+PSO lograron una tasa de finalización "
        "perfecta del 100,00 % en todas las semillas. El modo B redujo el viaje medio a 25,92 s y la espera a 0,89 s, "
        "mientras que B+PSO registró 27,01 s de viaje y 0,81 s de espera media con cero celdas críticas, evidenciando "
        "que en densidades bajas la navegación adaptativa garantiza un tránsito fluido y sin atascos."
    )

    doc.paragraphs[399].text = (
        "En S2 (80 agentes), el modo A colapsó a una tasa de finalización del 22,50 % con 132,85 s de espera media "
        "y un pico de 5,67 celdas críticas. El modo adaptativo B elevó la finalización al 100,00 % y redujo la espera "
        "media a 4,35 s. Por su parte, el modo B+PSO con parámetros calibrados optimizó aún más la respuesta: mantuvo "
        "el 100,00 % de finalización, descendió el tiempo de viaje penalizado a 29,20 s y disminuyó el tiempo de espera "
        "a solo 1,93 s (una reducción adicional del 55,6 % respecto a B), reduciendo la presencia de celdas críticas "
        "a un promedio de apenas 0,33."
    )

    doc.paragraphs[400].text = (
        "En S3 (120 agentes), el escenario de máxima densidad, se evidenció el colapso crítico del modo A por "
        "formación de arcos de compresión frente a la puerta estrecha, con una finalización media de apenas 25,28 % "
        "y una espera media de 130,44 s. El modo adaptativo estándar B mitigó la congestión elevando la finalización "
        "al 86,39 % y reduciendo la espera a 29,56 s, pero mantuvo 49 agentes bloqueados en la semilla 43 (71 llegados "
        "de 120). Finalmente, el modo B+PSO con parámetros calibrados por PSO (α* = 2,984, ks* = 2,000, kr* = 0,977) "
        "resolvió íntegramente el cuello de botella: alcanzó el 100,00 % de finalización en todas las semillas "
        "(120 de 120 agentes), redujo el tiempo de viaje a 32,46 s y abatió el tiempo de espera a solo 2,90 s "
        "(una reducción del 90,2 % frente a B y del 97,8 % frente a A), eliminando por completo la persistencia "
        "de celdas críticas (0,00)."
    )

    doc.paragraphs[401].text = (
        "No se registraron solapamientos físicos en ninguno de los instantes muestreados a lo largo de los 27 episodios "
        "evaluados, lo que confirma la estabilidad de las restricciones cinemáticas y de repulsión del motor. En cuanto "
        "a las decisiones adaptativas, se registraron 140, 361,67 y 657,00 cambios de ruta promedio en B+PSO para S1, "
        "S2 y S3, respectivamente. La mayor frecuencia de redireccionamiento en S3 refleja la capacidad del enjambre "
        "para redistribuir el flujo hacia la ruta alternativa antes de que la presión radial cierre el paso principal."
    )

    doc.paragraphs[402].text = (
        "Los resultados experimentales validan de forma contundente la hipótesis del proyecto: la integración de la "
        "detección espacial no supervisada (DBSCAN), la evaluación de persistencia en la grilla de diagnóstico y la "
        "navegación adaptativa A* calibrada mediante PSO previene la formación de atascos irreversibles, garantizando la "
        "evacuación total y reduciendo drásticamente los tiempos muertos de espera."
    )

    # FIGURA 5.9-1 (P404, P405, P406)
    print("7. Actualizando Figura 5.9-1 con gráfico V3...")
    doc.paragraphs[404].text = "Comparación de tiempo medio de viaje penalizado, espera y tasa de finalización en S1, S2 y S3 entre los modos A, B y B+PSO. Medias de tres semillas y desviación estándar descriptiva"
    doc.paragraphs[406].text = "Nota. Elaboración propia a partir de capturas/v3/comparacion_experimental_v3.png con los resultados de la batería V3."

    # Reemplazar blob de la imagen en P405
    p_img = doc.paragraphs[405]
    for r in p_img.runs:
        for blip in r._element.xpath('.//a:blip'):
            embed = blip.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed']
            part = doc.part.rels[embed].target_part
            with open('capturas/v3/comparacion_experimental_v3.png', 'rb') as f_img:
                part._blob = f_img.read()
            print("  -> Imagen Figura 5.9-1 sustituida con éxito.")

    # P408: PRUEBAS AUTOMÁTICAS
    print("8. Actualizando conteo de pruebas en sección 5.9 (P408)...")
    doc.paragraphs[408].text = (
        "Se ejecutaron con éxito las trece suites de pruebas automatizadas del proyecto (pruebas de entorno, "
        "dos rutas, motor de agentes, diagnóstico de congestión, telemetría, visualización base e integrada, "
        "DBSCAN optimizado con kd-tree, calibración PSO e interfaz web interactiva), acumulando más de 80 "
        "pruebas unitarias con un 100 % de aprobación mediante pruebas/ejecutar_todas.py. Se comprobó la "
        "integridad del acoplamiento físico a 0,1 s, la observación a 1,0 s, la carga dinámica de parámetros "
        "óptimos theta y la total reproducibilidad mediante semillas fijas."
    )

    # 7. CONCLUSIONES (P420)
    print("9. Actualizando Conclusiones (P420)...")
    doc.paragraphs[420].text = (
        "La calibración metaheurística mediante Optimización por Enjambre de Partículas (PSO) demostró ser el "
        "factor determinante para resolver los escenarios de alta densidad. Mientras que la adaptación estándar "
        "con parámetros fijos mitigaba la congestión de forma parcial, el vector óptimo calibrado en B+PSO "
        "(α* = 2,984, ks* = 2,000, kr* = 0,977) permitió a los agentes anticipar la saturación espacial, bifurcar "
        "el flujo de manera equilibrada hacia la ruta alternativa y alcanzar una tasa de evacuación del 100,00 % "
        "en todos los escenarios evaluados, reduciendo los tiempos de espera a niveles mínimos y eliminando la "
        "persistencia de celdas críticas."
    )

    print(f"Guardando documento actualizado en {destino}...")
    doc.save(destino)
    print(f"[OK] Archivo guardado correctamente ({os.path.getsize(destino)} bytes).")

if __name__ == "__main__":
    # Actualizar ambos archivos para sincronía total
    actualizar_documento("informe/2do PArcial IA Final.docx", "informe/2do PArcial IA.docx")
    actualizar_documento("informe/2do PArcial IA.docx", "informe/2do PArcial IA Final.docx")
    print("=== PROCESO DE ACTUALIZACIÓN CONCLUIDO CON ÉXITO ===")
