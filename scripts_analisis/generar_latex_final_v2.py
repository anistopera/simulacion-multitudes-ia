import docx
import os
import re

def escape_latex(text):
    if not text:
        return ""
    s = text
    s = s.replace('\\', '\\textbackslash{}')
    s = s.replace('&', '\\&')
    s = s.replace('%', '\\%')
    s = s.replace('#', '\\#')
    s = s.replace('_', '\\_')
    s = s.replace('{', '\\{')
    s = s.replace('}', '\\}')
    s = s.replace('~', '\\textasciitilde{}')
    s = s.replace('^', '\\textasciicircum{}')
    # Símbolos matemáticos comunes en texto
    s = s.replace('α*', '$\\alpha^*$')
    s = s.replace('α', '$\\alpha$')
    s = s.replace('θ*', '$\\theta^*$')
    s = s.replace('θ', '$\\theta$')
    s = s.replace('ks*', '$k_s^*$')
    s = s.replace('kr*', '$k_r^*$')
    s = s.replace('ks', '$k_s$')
    s = s.replace('kr', '$k_r$')
    s = s.replace('eps', '$\\varepsilon$')
    s = s.replace('ε', '$\\varepsilon$')
    s = s.replace('τ', '$\\tau$')
    s = s.replace('ρ', '$\\rho$')
    s = s.replace('v̄', '$\\bar{v}$')
    s = s.replace('A*', '$A^*$')
    s = s.replace('kd-tree', '$kd$-tree')
    s = s.replace('ball-tree', 'ball\\_tree')
    return s

def docx_to_latex(docx_path, tex_path):
    print(f"Cargando {docx_path}...")
    doc = docx.Document(docx_path)
    
    out = []
    
    # Preámbulo profesional: secnumdepth=0 evita duplicaciones de números en títulos
    out.append(r"""\documentclass[12pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-tabla]{babel}
\usepackage[margin=2.54cm]{geometry}
\usepackage{mathptmx}
\usepackage{setspace}
\onehalfspacing
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{float}
\usepackage{hyperref}
\usepackage{array,longtable,ragged2e}
\usepackage{caption}
\usepackage{titlesec}
\usepackage{fancyhdr}

\hypersetup{
    colorlinks=true,
    linkcolor=black,
    citecolor=black,
    urlcolor=blue,
    pdftitle={Simulación de multitudes y optimización de flujo en entornos interactivos},
    pdfauthor={Grupo 13, UMSS}
}

\setlength{\parindent}{1.27cm}
\setlength{\parskip}{6pt}
\setlength{\emergencystretch}{3em}

% Desactivar prefijos automáticos de LaTeX para evitar duplicar números (ej. 5.1 5.1.)
% Se conservan números en índice (\setcounter{tocdepth}{3}) y numeración secuencial de ecuaciones (1), (2)...
\setcounter{secnumdepth}{0}
\setcounter{tocdepth}{3}

\titleformat{\section}{\centering\large\bfseries}{}{0pt}{}
\titleformat{\subsection}{\normalsize\bfseries}{}{0pt}{}
\titleformat{\subsubsection}{\normalsize\bfseries\itshape}{}{0pt}{}

\captionsetup{
    font=small,
    labelfont=bf,
    labelsep=period,
    justification=justified
}

\begin{document}

% ==========================================
% PORTADA
% ==========================================
\begin{titlepage}
\centering
\setstretch{1.15}

\begin{figure}[H]
\centering
\includegraphics[height=2.2cm]{figuras_latex/logo_umss.png}
\hspace{3.5cm}
\includegraphics[height=2.2cm]{figuras_latex/logo_fcyt.png}
\end{figure}

\vspace{0.8cm}
{\bfseries\large UNIVERSIDAD MAYOR DE SAN SIMÓN}\par
{\bfseries\large FACULTAD DE CIENCIAS Y TECNOLOGÍA}\par
{\bfseries\normalsize INGENIERÍA EN SISTEMAS}\par

\vspace{1.5cm}
{\bfseries\Large SIMULACIÓN DE MULTITUDES Y OPTIMIZACIÓN DE FLUJO EN ENTORNOS INTERACTIVOS:}\\[0.3cm]
{\bfseries\large Detección no supervisada de cuellos de botella y optimización metaheurística del flujo}\par

\vspace{1.5cm}
\begin{flushleft}
\setlength{\parindent}{0cm}
\textbf{Área:} Aprendizaje no supervisado \\
\textbf{Subárea:} Clasificación y optimización \\
\textbf{Materia:} Inteligencia Artificial \\
\textbf{Docente:} Lic. Patricia Rodríguez Bilbao \\
\textbf{Carrera:} Ing. de Sistemas \\
\textbf{Grupo:} 13 \\[0.4cm]
\textbf{Integrantes:}
\begin{itemize}
    \setlength{\itemsep}{0pt}
    \setlength{\parskip}{0pt}
    \item Alba Zapata Cristhian
    \item Bustamante Escobar Jhosselin Sthaicy
    \item Choque Aguilar Wendy
    \item Flores Choquetopa Nicole Marisol
    \item Flores Mamani Daniel Teodoro
    \item Lora Quilla Santiago Leonardo
    \item Orellana Castro Keyla Yhajaira
    \item Padilla Alexander J.
\end{itemize}
\end{flushleft}

\vfill
{\normalsize Fecha: 25 de Noviembre del 2026}\par
{\bfseries\normalsize COCHABAMBA -- BOLIVIA}

\end{titlepage}

\newpage
\tableofcontents
\newpage
""")

    print(f"Procesando párrafos desde Introducción...")
    
    fig_map = {
        'figura 1': ('figura_1_esquema_conceptual.png', '0.85\\textwidth', 'Esquema conceptual del escenario bidimensional de dos rutas con entrada y salida comunes.'),
        'figura 5.1-1': ('figura_5_1_1_matriz_obstaculos.png', '0.75\\textwidth', 'Representación matricial y visual del escenario en entorno Pygame.'),
        'figura 5.1-2': ('figura_5_1_2a_prueba_entorno.png', '0.75\\textwidth', 'Verificación de conectividad y transitabilidad de rutas.'),
        'figura 5.1-3': ('figura_5_1_3_trayectorias_agentes.png', '0.85\\textwidth', 'Trayectorias individuales y respuesta de fuerzas sociales en evacuación.'),
        'figura 5.2-1': ('figura_5_2_1_interfaz_web_inicial.png', '0.90\\textwidth', 'Estado inicial de S3 con 120 peatones, modo A y semilla 43 en la interfaz web interactiva.'),
        'figura 5.2-2': ('figura_5_2_2_calor_y_grupos.png', '0.90\\textwidth', 'Inspección de acumulación crítica mediante capas de Calor (densidad local) y Grupos (clustering DBSCAN).'),
        'figura 5.2-3': ('figura_5_2_3_rutas_adaptativas.png', '0.90\\textwidth', 'Rutas previstas dinámicas en S3 con modo B+PSO bajo tema claro.'),
        'figura 5.2-4': ('figura_5_2_4_resumen_cierre.png', '0.70\\textwidth', 'Tarjeta de resumen y telemetría final de cierre tras evacuar el 100\\% de los agentes en B+PSO.'),
        'figura 5.4-1': ('figura_5_4_1_clusters_120.png', '0.85\\textwidth', 'Clústeres espaciales detectados por DBSCAN en S3 (120 agentes, t = 20 s).'),
        'figura 5.4-2': ('figura_5_4_2_evolucion_S3.png', '0.90\\textwidth', 'Evolución temporal del agrupamiento no supervisado en t = 1, 10, 20 y 60 s.'),
        'figura 5.4-3': ('figura_5_4_3_grupo_principal_tiempo.png', '0.85\\textwidth', 'Tamaño del grupo principal y velocidad media de sus miembros a lo largo del tiempo.'),
        'figura 5.4-4': ('figura_5_4_4_efecto_eps.png', '0.85\\textwidth', 'Efecto de la variación del radio de vecindad $\\varepsilon$ sobre la detección de grupos en S3.'),
        'figura 5.6-1': ('figura_5_6_1_comparacion_rutas.png', '0.85\\textwidth', 'Comparación de rutas del modo A y B ante congestión y efecto de las reglas anti-oscilación.'),
        'figura 5.9-1': ('figura_5_9_1_comparacion_v3.png', '0.95\\textwidth', 'Comparación experimental de tiempo de viaje penalizado, tiempo de espera y tasa de finalización entre Modos A, B y B+PSO.')
    }

    total_p = len(doc.paragraphs)
    i = 63 # Inicio en Introducción

    while i < total_p:
        p = doc.paragraphs[i]
        txt = p.text.strip()
        style = p.style.name

        if not txt:
            i += 1
            continue

        # ==========================================
        # RECONOCIMIENTO ORDENADO DE ENCABEZADOS
        # ==========================================
        if txt.startswith("1. Introducción") or txt == "Introducción":
            out.append(r"\section{I. Introducción}")
        elif txt.startswith("1.1.") or txt == "Contexto del problema":
            out.append(r"\subsection{1.1. Contexto del problema}")
        elif txt.startswith("1.2.") or txt == "Planteamiento del problema":
            out.append(r"\subsection{1.2. Planteamiento del problema}")
        elif txt.startswith("1.3.") or txt == "Justificación":
            out.append(r"\subsection{1.3. Justificación}")
        elif txt.startswith("2. Objetivos") or txt == "Objetivos":
            out.append(r"\section{II. Objetivos}")
        elif txt.startswith("2.1.") or txt == "Objetivo general":
            out.append(r"\subsection{2.1. Objetivo general}")
        elif txt.startswith("2.2.") or txt == "Objetivos específicos":
            out.append(r"\subsection{2.2. Objetivos específicos}")
        elif txt.startswith("3. Marco teórico") or txt == "Marco teórico":
            out.append(r"\section{III. Marco teórico}")
        elif txt.startswith("3.11."):
            out.append(r"\subsection{3.11. Calidad del agrupamiento}")
        elif txt.startswith("3.10."):
            out.append(r"\subsection{3.10. Evaluación experimental}")
        elif txt.startswith("3.1."):
            out.append(r"\subsection{3.1. Aprendizaje no supervisado}")
        elif txt.startswith("3.2."):
            out.append(r"\subsection{3.2. Clasificación y optimización}")
        elif txt.startswith("3.3."):
            out.append(r"\subsection{3.3. Agrupamiento (clustering)}")
        elif txt.startswith("3.4."):
            out.append(r"\subsection{3.4. DBSCAN}")
        elif txt.startswith("3.5."):
            out.append(r"\subsection{3.5. Técnicas complementarias}")
        elif txt.startswith("3.6."):
            out.append(r"\subsection{3.6. Simulación basada en agentes}")
        elif txt.startswith("3.7."):
            out.append(r"\subsection{3.7. Densidad, congestión y cuellos de botella}")
        elif txt.startswith("3.8."):
            out.append(r"\subsection{3.8. Planificación de rutas con A*}")
        elif txt.startswith("3.9."):
            out.append(r"\subsection{3.9. Optimización con PSO}")
        elif txt.startswith("4. Marco referencial") or txt == "Marco referencial":
            out.append(r"\section{IV. Marco referencial}")
        elif txt.startswith("4.1.") or txt.startswith("Antecedentes del dominio"):
            out.append(r"\subsection{4.1. Antecedentes del dominio y problemáticas de circulación}")
        elif txt.startswith("4.2.") or txt.startswith("Caracterización del escenario"):
            out.append(r"\subsection{4.2. Caracterización del escenario de estudio}")
        elif txt.startswith("4.3.") or txt.startswith("Delimitación del sistema"):
            out.append(r"\subsection{4.3. Delimitación del sistema}")
        elif txt.startswith("5. Ingeniería") or txt == "Ingeniería":
            out.append(r"\section{V. Ingeniería del proyecto}")
        elif txt.startswith("5.1.1"):
            out.append(r"\subsubsection{5.1.1. Diseño del escenario}")
        elif txt.startswith("5.1.2"):
            out.append(r"\subsubsection{5.1.2. Representación del entorno}")
        elif txt.startswith("5.1.3"):
            out.append(r"\subsubsection{5.1.3. Implementación del motor del escenario}")
        elif txt.startswith("5.1.4"):
            out.append(r"\subsubsection{5.1.4. Visualización del escenario}")
        elif txt.startswith("5.1.5"):
            out.append(r"\subsubsection{5.1.5. Pruebas de funcionamiento}")
        elif txt.startswith("5.1.6") or "Motor de agentes" in txt:
            out.append(r"\subsubsection{5.1.6. Motor de agentes y dinámicas de interacción}")
        elif txt.startswith("5.1.") or txt.startswith("5.1 "):
            out.append(r"\subsection{5.1. Entorno de simulación}")
        elif txt.startswith("5.2"):
            out.append(r"\subsection{5.2. Interfaz y visualización interactiva del simulador}")
        elif txt.startswith("5.3"):
            out.append(r"\subsection{5.3. Telemetría y registro en CSV}")
        elif txt.startswith("5.4.1"):
            out.append(r"\subsubsection{5.4.1. Función del módulo}")
        elif txt.startswith("5.4.2"):
            out.append(r"\subsubsection{5.4.2. Parámetros de detección}")
        elif txt.startswith("5.4.3"):
            out.append(r"\subsubsection{5.4.3. Implementación y optimización espacial}")
        elif txt.startswith("5.4.4"):
            out.append(r"\subsubsection{5.4.4. Datos y calibración}")
        elif txt.startswith("5.4.5"):
            out.append(r"\subsubsection{5.4.5. Resultados y evolución temporal}")
        elif txt.startswith("5.4.6"):
            out.append(r"\subsubsection{5.4.6. Calidad del agrupamiento}")
        elif txt.startswith("5.4.7"):
            out.append(r"\subsubsection{5.4.7. Valores adoptados y limitaciones}")
        elif txt.startswith("5.4.") or txt.startswith("5.4 "):
            out.append(r"\subsection{5.4. Detección no supervisada con DBSCAN}")
        # PREFIJOS DE 5.5 ORDENADOS ESTRICTAMENTE
        elif txt.startswith("5.5.1"):
            out.append(r"\subsubsection{5.5.1. Discretización espacial y métricas locales}")
        elif txt.startswith("5.5.2"):
            out.append(r"\subsubsection{5.5.2. Reglas de clasificación y umbrales operativos}")
        elif txt.startswith("5.5.3"):
            out.append(r"\subsubsection{5.5.3. Generación de la señal de costo para la navegación adaptativa}")
        elif txt.startswith("5.5.4"):
            out.append(r"\subsubsection{5.5.4. Verificación experimental con 120 agentes}")
        elif txt.startswith("5.5.") or txt.startswith("5.5 ") or txt == "5.5 Diagnóstico de zonas":
            out.append(r"\subsection{5.5. Diagnóstico de zonas y cuadrícula espacial}")
        elif txt.startswith("5.6"):
            out.append(r"\subsection{5.6. Navegación adaptativa con A* y calibración PSO}")
        elif txt.startswith("5.7"):
            out.append(r"\subsection{5.7. Arquitectura modular e integración del ciclo}")
        elif txt.startswith("5.8"):
            out.append(r"\subsection{5.8. Tecnologías y herramientas}")
        elif txt.startswith("5.9"):
            out.append(r"\subsection{5.9. Pruebas y resultados experimentales}")
        elif txt.startswith("6. Conclusiones") or txt == "Conclusiones":
            out.append(r"\section{VI. Conclusiones}")
        elif txt.startswith("7. Bibliografía") or txt == "Bibliografía":
            out.append(r"\section{VII. Bibliografía}")

        # ==========================================
        # FIGURAS
        # ==========================================
        elif txt.lower().startswith("figura "):
            key_match = None
            for k in fig_map:
                if k in txt.lower():
                    key_match = k
                    break
            
            if key_match:
                img_file, scale, caption_desc = fig_map[key_match]
                note_text = "Elaboración propia."
                for look in range(i+1, min(i+4, total_p)):
                    look_txt = doc.paragraphs[look].text.strip()
                    if look_txt.startswith("Nota."):
                        note_text = look_txt
                        break
                    elif len(look_txt) > 20 and not look_txt.startswith("Figura"):
                        caption_desc = look_txt

                out.append(f"""
\\begin{{figure}}[H]
\\centering
\\includegraphics[width={scale}]{{figuras_latex/{img_file}}}
\\caption{{{escape_latex(caption_desc)}}}
\\vspace{{2pt}}
{{\\footnotesize \\textit{{{escape_latex(note_text)}}}}}
\\end{{figure}}
""")
                while i + 1 < total_p and (doc.paragraphs[i+1].text.strip().startswith("Nota.") or (len(doc.paragraphs[i+1].runs) > 0 and doc.paragraphs[i+1].runs[0]._element.xpath('.//a:blip'))):
                    i += 1

        # ==========================================
        # TABLAS FORMATEADAS EN BOOKTABS
        # ==========================================
        elif txt.startswith("Tabla 5.1-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Parámetros iniciales del motor de agentes.}
\small
\begin{tabular}{ll}
\toprule
\textbf{Parámetro} & \textbf{Valor inicial} \\
\midrule
Paso de tiempo físico ($\Delta t$) & 0,10 s \\
Radio del agente & 0,25 m \\
Velocidad deseada & Uniforme en $[0,9;\ 1,5]$ m/s \\
Fuerza al objetivo ($k_o$) & 1,0 \\
Fuerza de separación ($k_s$) & 1,5 \\
Fuerza de obstáculos ($k_r$) & 2,0 \\
Radio de interacción & 1,20 m \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Parámetros base del Modelo de Fuerzas Sociales. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.2-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Controles interactivos de la interfaz web y efecto en la simulación.}
\small
\begin{tabular}{lll}
\toprule
\textbf{Control} & \textbf{Atajo} & \textbf{Efecto en el episodio} \\
\midrule
Modos A / B / B+PSO & 1 / 2 / 3 & Selecciona estrategia de navegación (reinicia a 0,0 s) \\
Escenario S1 / S2 / S3 & 4 / 5 / 6 & Carga 40, 80 o 120 agentes (reinicia a 0,0 s) \\
Semilla 42 / 43 / 44 & 7 / 8 / 9 & Disposición inicial reproducible de la población \\
Iniciar / Pausa & Espacio & Alterna reproducción continua a tiempo simulado \\
Paso a paso & P & Avanza un único paso físico de 0,1 s \\
Reiniciar & R & Devuelve el estado a 0,0 s en pausa \\
Velocidad $\times 1, \times 2, \times 4$ & V & Multiplica tasa de avance manteniendo $\Delta t = 0,1$ s \\
Capas (Calor, Grupos, Rutas) & H, C, L & Conmuta superposición diagnóstica sobre el lienzo \\
Tema claro / oscuro & T & Alterna contraste visual según iluminación \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Controles de arquitectura desacoplada mediante Web API. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.3-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Muestra representativa de registros de telemetría individual.}
\small
\begin{tabular}{rrrrrrrr}
\toprule
\textbf{$t$ (s)} & \textbf{id} & \textbf{$x$ (m)} & \textbf{$y$ (m)} & \textbf{$v_x$ (m/s)} & \textbf{$v_y$ (m/s)} & \textbf{$d_{\text{vecino}}$ (m)} & \textbf{$t_{\text{bloqueo}}$ (s)} \\
\midrule
1,0 & 0 & 3,25 & 10,80 & 1,12 & 0,05 & 0,62 & 0,0 \\
1,0 & 1 & 2,80 & 11,20 & 0,95 & -0,10 & 0,58 & 0,0 \\
20,0 & 0 & 14,20 & 11,05 & 0,15 & 0,02 & 0,38 & 12,4 \\
20,0 & 1 & 13,85 & 10,90 & 0,08 & -0,01 & 0,35 & 15,1 \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Registros exportados cada 1,0 s por modulos/telemetria.py. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.4-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Parámetros iniciales de calibración de DBSCAN.}
\small
\begin{tabular}{lll}
\toprule
\textbf{Parámetro} & \textbf{Valor inicial} & \textbf{Significado físico} \\
\midrule
$\varepsilon$ (eps) & 1,20 m & Radio de vecindad de influencia peatonal \\
$min\_samples$ & 5 & Densidad mínima para considerar núcleo de congestión \\
Métrica & Euclidiana & Distancia física en coordenadas continuas $(x, y)$ \\
Algoritmo & $kd$-tree & Búsqueda espacial optimizada ($O(N \log N)$) \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Configuración base para detección en tiempo real. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.4-2") or txt.startswith("Tabla 5.4-3") or txt.startswith("Tabla 5.4-4"):
            pass
        elif txt.startswith("Tabla 5.5-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Parámetros del módulo de diagnóstico de congestión.}
\small
\begin{tabular}{llll}
\toprule
\textbf{Variable} & \textbf{Símbolo} & \textbf{Valor} & \textbf{Criterio técnico} \\
\midrule
Tamaño de celda & $L_d$ & 2,0 m & Resolución compatible con la escala de paso \\
Superficie transitable & $A_z$ & 4,0 m$^2$ & Área libre de obstáculos en la cuadrícula \\
Umbral de acumulación & $\rho_{\text{acum}}$ & 1,5 agentes/m$^2$ & Inicio de reducción de velocidad libre \\
Umbral crítico & $\rho_{\text{crit}}$ & 2,0 agentes/m$^2$ & Límite de flujo estable (Fruin, 1971) \\
Razón de bloqueo & $v_{\text{umbral}}$ & 0,5 $\bar{v}_{\text{des}}$ & Criterio de pérdida de fluidez \\
Persistencia temporal & $\tau_{\text{pers}}$ & 3,0 s & Filtro pasabajo contra frenadas puntuales \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Parámetros de discretización espacial y temporal. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.5-2"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Matriz de decisión para la clasificación operativa de zonas de diagnóstico.}
\small
\begin{tabular}{llll}
\toprule
\textbf{Estado} & \textbf{Densidad ($\rho$)} & \textbf{Velocidad ($\bar{v}$)} & \textbf{Persistencia} \\
\midrule
0: Libre & $\rho < 1,5$ ag/m$^2$ & Normal & Sin restricción \\
1: Acumulación & $\rho \ge 1,5$ ag/m$^2$ & Parcial & $< 3,0$ s \\
2: Crítico & $\rho \ge 2,0$ ag/m$^2$ & $\le 0,5 \cdot \bar{v}_{\text{des}}$ & $\ge 3,0$ s consecutivos \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Reglas de transición de estados y matriz de costo D. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.6-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Parámetros de la navegación adaptativa y vector óptimo PSO.}
\small
\begin{tabular}{lll}
\toprule
\textbf{Parámetro} & \textbf{Valor base / Calibrado} & \textbf{Función en el algoritmo} \\
\midrule
Penalización congestión ($\alpha$) & 2,00 / \textbf{2,984*} & Ponderación del costo de densidad en $A^*$ \\
Repulsión agentes ($k_s$) & 1,50 / \textbf{2,000*} & Magnitud de fuerza interpersonal \\
Repulsión obstáculos ($k_r$) & 2,00 / \textbf{0,977*} & Magnitud de amortiguación contra paredes \\
Intervalo de replanificación ($\tau$) & 4,00 s & Período mínimo entre consultas de ruta \\
Margen de mejora & 10 \% & Histéresis contra oscilaciones de ruta \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Valores con asterisco (*) corresponden a la convergencia metaheurística de PSO. Elaboración propia.}}
\end{table}
""")
        elif txt.startswith("Tabla 5.9-1"):
            out.append(r"""
\begin{table}[H]
\centering
\caption{Resultados medios de los 27 episodios V3: tres semillas por escenario y modo de navegación.}
\small
\begin{tabular}{cclrrrrrr}
\toprule
\textbf{Esc.} & \textbf{Agentes} & \textbf{Modo} & \textbf{Viaje (s)} & \textbf{Espera (s)} & \textbf{Fin. (\%)} & \textbf{Solap.} & \textbf{Crít. máx.} & \textbf{Cambios} \\
\midrule
S1 & 40 & A & 61,08 & 41,34 & 76,67 & 0,00 & 0,33 & 0,00 \\
S1 & 40 & B & 25,92 & 0,89 & 100,00 & 0,00 & 0,00 & 110,33 \\
S1 & 40 & \textbf{B+PSO} & \textbf{27,01} & \textbf{0,81} & \textbf{100,00} & \textbf{0,00} & \textbf{0,00} & \textbf{140,00} \\
\midrule
S2 & 80 & A & 143,94 & 132,85 & 22,50 & 0,00 & 5,67 & 0,00 \\
S2 & 80 & B & 30,52 & 4,35 & 100,00 & 0,00 & 1,00 & 343,67 \\
S2 & 80 & \textbf{B+PSO} & \textbf{29,20} & \textbf{1,93} & \textbf{100,00} & \textbf{0,00} & \textbf{0,33} & \textbf{361,67} \\
\midrule
S3 & 120 & A & 141,89 & 130,44 & 25,28 & 0,00 & 8,67 & 0,00 \\
S3 & 120 & B & 54,66 & 29,56 & 86,39 & 0,00 & 3,33 & 566,67 \\
S3 & 120 & \textbf{B+PSO} & \textbf{32,46} & \textbf{2,90} & \textbf{100,00} & \textbf{0,00} & \textbf{0,00} & \textbf{657,00} \\
\bottomrule
\end{tabular}
\vspace{2pt}
{\footnotesize \textit{Nota. Datos de capturas/v3/tabla\_comparativa\_v3.csv; promedios sobre 27 episodios evaluados. Elaboración propia.}}
\end{table}
""")

        # ==========================================
        # ECUACIONES MATEMÁTICAS FORMALES NUMERADAS
        # ==========================================
        # 1. Optimización general (3.2)
        elif "En esta expresión, θ es el vector de decisión" in txt:
            out.append(r"""
\begin{equation}
\min_{\theta \in \Omega} J(\theta)
\label{eq:optimizacion_general}
\end{equation}
""" + f"{escape_latex(txt)}\\par\n")

        # 2. DBSCAN: Distancia y vecindad (3.4)
        elif "Para observaciones bidimensionales, la distancia euclidiana" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
d(p, q) = \sqrt{(x_p - x_q)^2 + (y_p - y_q)^2}
\label{eq:distancia_euclidiana}
\end{equation}
\begin{equation}
N_\varepsilon(p) = \{q \in D \mid d(p, q) \le \varepsilon\}
\label{eq:vecindad_dbscan}
\end{equation}
\begin{equation}
|N_\varepsilon(p)| \ge \text{MinPts}
\label{eq:condicion_nucleo}
\end{equation}
""")

        # 3. Dinámica de agentes: Integración y fuerzas (3.6)
        elif "Una aproximación temporal de primer orden actualiza la posición" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
\vec{p}_i(t + \Delta t) = \vec{p}_i(t) + \vec{v}_i(t + \Delta t) \Delta t
\label{eq:integracion_euler}
\end{equation}
""")
        elif "El modelo de fuerzas sociales interpreta el movimiento peatonal mediante términos" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
m_i \frac{d\vec{v}_i}{dt} = \vec{F}_i = k_o \vec{F}_{\text{objetivo}} + k_s \vec{F}_{\text{separación}} + k_r \vec{F}_{\text{obstáculos}}
\label{eq:fuerzas_sociales}
\end{equation}
\begin{equation}
\vec{F}_{\text{objetivo}} = \frac{v_{\text{des}} \vec{e}_i - \vec{v}_i}{\tau_{\text{rel}}}
\label{eq:fuerza_deseada}
\end{equation}
""")

        # 4. Densidad y velocidad media (3.7)
        elif "La rapidez media resume los módulos de velocidad" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
\rho(z, t) = \frac{N(z, t)}{A(z)}
\label{eq:densidad_espacial}
\end{equation}
\begin{equation}
\bar{v}(z, t) = \frac{1}{N(z, t)} \sum_{i \in z} \|\vec{v}_i(t)\|
\label{eq:velocidad_media}
\end{equation}
""")

        # 5. Búsqueda A* (3.8)
        elif "Evalúa los nodos mediante la suma del costo acumulado desde el origen" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
f(n) = g(n) + h(n)
\label{eq:astar_evaluacion}
\end{equation}
\begin{equation}
c(u, v) = L(u, v) \cdot \bigl(1 + \alpha \cdot D(v, t)\bigr)
\label{eq:costo_arista_astar}
\end{equation}
""")

        # 6. PSO (3.9)
        elif "Su desplazamiento combina inercia, experiencia individual e información compartida" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
\vec{v}_p^{(k+1)} = w \vec{v}_p^{(k)} + c_1 r_1 \bigl(\vec{b}_p - \vec{x}_p^{(k)}\bigr) + c_2 r_2 \bigl(\vec{b}_g - \vec{x}_p^{(k)}\bigr)
\label{eq:pso_velocidad}
\end{equation}
\begin{equation}
\vec{x}_p^{(k+1)} = \vec{x}_p^{(k)} + \vec{v}_p^{(k+1)}
\label{eq:pso_posicion}
\end{equation}
""")
        elif "Una función objetivo con varios criterios puede combinar términos normalizados" in txt:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
J(\theta) = w_1 \frac{\bar{T}_{\text{viaje}}}{T_{\text{base}}} + w_2 \frac{\bar{T}_{\text{espera}}}{T_{\text{base}}} + w_3 P_{\text{no\_llegados}}
\label{eq:pso_funcion_costo}
\end{equation}
""")

        # 7. Calidad del agrupamiento: Silueta (3.11)
        elif "3.11. Calidad del agrupamiento" in doc.paragraphs[i-1].text:
            out.append(f"{escape_latex(txt)}\\par\n" + r"""
\begin{equation}
s(i) = \frac{b(i) - a(i)}{\max\bigl(a(i), b(i)\bigr)}
\label{eq:coeficiente_silueta}
\end{equation}
""")

        # 8. Matriz D en Ingeniería (5.5.3)
        elif "D(e, t) = min( 1,0 ; ρ(e, t) / 2,0 )" in txt:
            out.append(r"""
\begin{equation}
D(z, t) = \min\left(1,0;\ \frac{\rho(z, t)}{2,0}\right)
\label{eq:matriz_d_costo}
\end{equation}
""")

        # ==========================================
        # PÁRRAFOS REGULARES DE TEXTO
        # ==========================================
        else:
            esc_txt = escape_latex(txt)
            
            # Inserción de referencias cruzadas a ecuaciones en Ingeniería (POST-ESCAPE)
            # 1. Enlaces en 5.1.6 Motor de agentes
            if "Helbing y Moln" in esc_txt and "fuerzas sociales" in esc_txt:
                esc_txt = esc_txt.replace(
                    "Helbing y Molnár (1995)",
                    "Helbing y Molnár (1995), aplicando la integración cinemática de la Ecuación~(\\ref{eq:integracion_euler}) y la formulación de fuerzas de la Ecuación~(\\ref{eq:fuerzas_sociales})"
                )
            if "objetivo + k" in esc_txt and "obst" in esc_txt:
                esc_txt = esc_txt.replace(
                    "Fᵢ = kₒF\\_objetivo + kₛF\\_separación + kᵣF\\_obstáculos",
                    "$\\vec{F}_i = k_o \\vec{F}_{\\text{objetivo}} + k_s \\vec{F}_{\\text{separación}} + k_r \\vec{F}_{\\text{obstáculos}}$ de la Ecuación~(\\ref{eq:fuerzas_sociales})"
                )
            if "MotorAgentes actualiza posiciones y velocidades aplicando fuerzas sociales" in esc_txt:
                esc_txt = esc_txt.replace(
                    "MotorAgentes actualiza posiciones y velocidades aplicando fuerzas sociales y restricciones geométricas.",
                    "MotorAgentes actualiza posiciones y velocidades aplicando la integración cinemática de la Ecuación~(\\ref{eq:integracion_euler}) y el modelo de fuerzas sociales de Helbing de la Ecuación~(\\ref{eq:fuerzas_sociales}) con restricciones geométricas."
                )
            # 2. Enlaces en 5.4.3 DBSCAN
            if "DBSCAN detecta grupos con" in esc_txt and "min\\_samples=5" in esc_txt:
                esc_txt = esc_txt.replace(
                    "DBSCAN detecta grupos con $\\varepsilon$=1,2 m y min\\_samples=5.",
                    "DBSCAN detecta grupos evaluando la vecindad de la Ecuación~(\\ref{eq:vecindad_dbscan}) mediante la distancia euclidiana de la Ecuación~(\\ref{eq:distancia_euclidiana}) y la condición de núcleo de la Ecuación~(\\ref{eq:condicion_nucleo})."
                )
            if "detectar\\_grupos(posiciones," in esc_txt:
                esc_txt = esc_txt.replace(
                    "detectar\\_grupos(posiciones, $\\varepsilon$, min\\_samples): aplica DBSCAN",
                    "detectar\\_grupos(posiciones, $\\varepsilon$, min\\_samples): aplica DBSCAN conforme a las Ecuaciones~(\\ref{eq:distancia_euclidiana})--(\\ref{eq:condicion_nucleo})"
                )
            if "calcula el coeficiente Silhouette y el" in esc_txt:
                esc_txt = esc_txt.replace(
                    "calcula el coeficiente Silhouette y el índice Davies–Bouldin",
                    "calcula el coeficiente Silhouette de la Ecuación~(\\ref{eq:coeficiente_silueta}) y el índice Davies–Bouldin"
                )
            # 3. Enlaces en 5.5 Diagnóstico de zonas
            if "densidad espacial local y la velocidad media local" in esc_txt:
                esc_txt = esc_txt.replace(
                    "evalúa la densidad espacial local y la velocidad media local.",
                    "evalúa la densidad espacial local de la Ecuación~(\\ref{eq:densidad_espacial}) y la velocidad media de la Ecuación~(\\ref{eq:velocidad_media})."
                )
            if "diagnóstico convierte el mapa de densidades en la matriz de costo normalizada:" in esc_txt:
                esc_txt = esc_txt.replace(
                    "diagnóstico convierte el mapa de densidades en la matriz de costo normalizada:",
                    "diagnóstico convierte el mapa de densidades en la matriz de costo normalizada definida en la Ecuación~(\\ref{eq:matriz_d_costo}):"
                )
            if "Tabla 1 y la matriz de clasificación en la Tabla 2" in esc_txt:
                esc_txt = esc_txt.replace(
                    "Tabla 1 y la matriz de clasificación en la Tabla 2",
                    "Tabla 5.5-1 y la matriz de clasificación en la Tabla 5.5-2"
                )
            # 4. Enlaces en 5.6 Navegación y PSO
            if "evalúa , donde h(n) es la distancia euclidiana" in esc_txt:
                esc_txt = esc_txt.replace(
                    "evalúa , donde h(n) es la distancia euclidiana al destino. El costo de cada tramo es , donde L(e) es la longitud del tramo,  es el valor entregado por el diagnóstico de congestión y $\\alpha$ $\\ge$ 0 controla cuánto se evita la zona densa.",
                    "evalúa la función $f(n)$ de la Ecuación~(\\ref{eq:astar_evaluacion}), donde $h(n)$ es la distancia euclidiana al destino. El costo de cada tramo se penaliza según la Ecuación~(\\ref{eq:costo_arista_astar}) utilizando la matriz $D$ de la Ecuación~(\\ref{eq:matriz_d_costo}), donde $\\alpha \\ge 0$ pondera la aversión a la congestión."
                )
            if "minimizando el tiempo de tránsito, el tiempo de espera y las penalizaciones por agentes no evacuados bajo el escenario crítico S3." in esc_txt:
                esc_txt = esc_txt.replace(
                    "minimizando el tiempo de tránsito, el tiempo de espera y las penalizaciones por agentes no evacuados bajo el escenario crítico S3.",
                    "minimizando la función de costo multiobjetivo $J(\\theta)$ de la Ecuación~(\\ref{eq:pso_funcion_costo}) bajo las reglas de actualización de partículas de las Ecuaciones~(\\ref{eq:pso_velocidad}) y (\\ref{eq:pso_posicion}) sobre el escenario crítico S3."
                )

            # Formato de viñetas
            if style == 'List Bullet' or esc_txt.startswith('•') or esc_txt.startswith('-'):
                item_txt = esc_txt.lstrip('•- ')
                out.append(f"\\begin{{itemize}}\n\\item {item_txt}\n\\end{{itemize}}")
            else:
                out.append(f"{esc_txt}\\par\n")

        i += 1

    out.append(r"\end{document}")
    
    tex_content = "\n".join(out)
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    
    print(f"[OK] Archivo LaTeX guardado en {tex_path} ({len(tex_content)} caracteres).")

if __name__ == "__main__":
    docx_to_latex('informe/2do PArcial IA Final (1).docx', 'informe/2do_Parcial_IA_Final.tex')
    docx_to_latex('informe/2do PArcial IA Final (1).docx', 'informe/2do_Parcial_IA_Corregido.tex')
