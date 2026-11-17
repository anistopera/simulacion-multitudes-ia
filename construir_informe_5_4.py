"""Arma informe/Seccion_5_4_DBSCAN.docx a partir de capturas_dbscan/calibracion_dbscan.csv."""
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CAP = "capturas_dbscan"
df = pd.read_csv(f"{CAP}/calibracion_dbscan.csv")
c = lambda x, d=1: f"{x:.{d}f}".replace(".", ",")
d = lambda e, eps, m: df[(df.escenario == e) & (df.eps == eps) & (df.min_samples == m)].iloc[0]

doc = Document()
s = doc.sections[0]
s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.line_spacing = 1.5; st.paragraph_format.space_after = Pt(6)

def H(t, sz=13):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = True; r.font.size = Pt(sz)
    p.paragraph_format.keep_with_next = True; p.paragraph_format.space_before = Pt(10)
def P(t):
    p = doc.add_paragraph(t); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
def B(t):
    p = doc.add_paragraph(style="List Bullet"); p.add_run(t); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
def cap(t):
    p = doc.add_paragraph(); r = p.add_run(t); r.italic = True; r.font.size = Pt(10.5)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing = 1.0
def shade(cell):
    pr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), "E7E9ED"); pr.append(sh)
def table(head, rows, size=10):
    t = doc.add_table(rows=1, cols=len(head)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(head):
        cl = t.rows[0].cells[i]; cl.text = ""; r = cl.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size)
        cl.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER; shade(cl)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in t.rows:
        for cl in row.cells:
            for p in cl.paragraphs: p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(2)
def fig(path, w, t):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(path, width=Cm(w)); p.paragraph_format.keep_with_next = True; cap(t)


H("5.4. Detección con DBSCAN", 14)

H("5.4.1. Función del módulo")
P("Este módulo detecta en qué lugares del recinto se concentran los agentes. Recibe las posiciones [x, y] de los agentes activos en un instante, expresadas en metros y tomadas de la telemetría (5.3) o directamente del motor de agentes (5.2), y devuelve para cada agente una etiqueta de grupo (o −1 si es ruido) y, para cada grupo, su tamaño y su centro. Se ejecuta cada 1 s de simulación. Su resultado es la entrada del diagnóstico de zonas (5.5), que decide si una concentración es realmente una congestión.")
P("Un grupo detectado indica que hay agentes juntos, pero no que estén detenidos. Por eso este módulo no clasifica la congestión: solo localiza concentraciones. La clasificación en flujo libre, acumulación o congestión crítica se hace en 5.5 con la densidad, la velocidad y la persistencia. El módulo usa únicamente coordenadas físicas (x, y) en metros, como el motor del escenario (5.1); no consulta la matriz del mapa, que se indexa como [fila, columna].")

H("5.4.2. Parámetros")
table(["Parámetro", "Valor inicial", "Significado"],
      [["ε (eps)", "1,2 m", "Distancia máxima para que dos agentes sean vecinos"],
       ["min_samples", "5 agentes", "Mínimo de agentes en la vecindad de un punto, contándolo a él"],
       ["Entrada", "Arreglo (n, 2)", "Posiciones [x, y] en metros de los agentes activos"],
       ["Frecuencia", "Cada 1 s", "Intervalo de análisis"]], 10.5)
cap("Tabla 5.4-1. Parámetros iniciales de DBSCAN")
P("Se usan solo las coordenadas espaciales en metros, de modo que ε conserva un significado físico: 1,2 m equivale a 2,4 veces el diámetro de un agente (0,5 m). Se utilizó la implementación sklearn.cluster.DBSCAN de scikit-learn.")

H("5.4.3. Implementación")
P("El código está en el archivo modulos/dbscan_deteccion.py y expone las siguientes funciones:")
B("detectar_grupos(posiciones, eps, min_samples): aplica DBSCAN y devuelve las etiquetas por agente (−1 = ruido) y una lista de grupos, cada uno con su identificador, tamaño y centro (media de las posiciones de sus miembros), ordenada de mayor a menor.")
B("calidad_agrupamiento(posiciones, etiquetas): calcula el coeficiente Silhouette y el índice Davies–Bouldin solo cuando hay al menos dos grupos. El ruido se excluye del cálculo porque no constituye un grupo. Si no se cumple la condición, devuelve valores nulos.")
B("proporcion_ruido(etiquetas): fracción de agentes que no pertenecen a ningún grupo.")
B("calibrar(instantes, eps_lista, minpts_lista): prueba todas las combinaciones de ε y min_samples sobre una lista de instantes y devuelve el promedio de grupos, de ruido y de calidad.")
B("cargar_instantes_csv(ruta): lee un CSV con las columnas t, x e y (por ejemplo, el de telemetría) y devuelve un arreglo [x, y] por cada segundo.")

H("5.4.4. Datos y calibración")
P("La calibración se hizo con las posiciones generadas por el motor de agentes (5.2) en los tres escenarios de carga: S1 con 40 agentes, S2 con 80 y S3 con 120. Se simularon 60 s con la ruta fija (sin adaptación) y las semillas 42, 43 y 44, y se guardó la posición de los agentes activos cada 1 s. Los agentes que ya llegaron a la salida no se incluyen. En total se analizaron 128 instantes de S1, 180 de S2 y 180 de S3 (en S1 hay menos porque en dos de las tres semillas todos los agentes llegaron antes de los 60 s). Estos datos aún no pasan por el módulo de telemetría; cuando exista su CSV, la misma calibración se puede repetir sin cambios de código.")
P("Se probaron los valores ε ∈ {0,8; 1,0; 1,2; 1,5; 2,0} m y min_samples ∈ {3, …, 8} (30 combinaciones por escenario). Las tablas 5.4-2 a 5.4-4 muestran el número promedio de grupos y el porcentaje promedio de ruido.")
mps = list(range(3, 9)); epss = [0.8, 1.0, 1.2, 1.5, 2.0]
for esc, n, k in (("S1", 40, 2), ("S2", 80, 3), ("S3", 120, 4)):
    sub = df[df.escenario == esc]; rows = []
    for e in epss:
        row = [c(e)]
        for m in mps:
            r = sub[(sub.eps == e) & (sub.min_samples == m)].iloc[0]
            row.append(f"{c(r.clusters_prom)} / {c(r.ruido_pct, 0)} %")
        rows.append(row)
    table(["ε (m)"] + [f"min_samples = {m}" for m in mps], rows, 9)
    cap(f"Tabla 5.4-{k}. Grupos promedio / porcentaje de ruido, {esc} ({n} agentes)")

H("5.4.5. Resultados")
a, b, g = d("S1", 1.2, 5), d("S2", 1.2, 5), d("S3", 1.2, 5)
P(f"Con los valores iniciales (ε = 1,2 m, min_samples = 5), el módulo detectó en promedio {c(a.clusters_prom)} grupos en S1, {c(b.clusters_prom)} en S2 y {c(g.clusters_prom)} en S3, con {c(a.ruido_pct,0)} %, {c(b.ruido_pct,0)} % y {c(g.ruido_pct,0)} % de ruido. En todos los casos hay un grupo principal que contiene casi todos los agentes y, a veces, un grupo pequeño de agentes que ya cruzaron. La Figura 5.4-1 muestra un instante de S3 (t = 20 s): un grupo de 92 agentes frente al paso principal, con su centro en (12,1; 11,3) m, y un grupo de 5 agentes ya del otro lado.")
fig(f"{CAP}/fig_clusters_120.png", 14.5, "Figura 5.4-1. Grupos detectados en S3 (120 agentes) a los 20 s, semilla 42")
P("La Figura 5.4-2 sigue el mismo escenario en el tiempo. Al inicio (t = 1 s) los agentes están separados por unos 0,6 m en la zona de entrada, y DBSCAN los reúne en un solo grupo de 118 agentes aunque todos se mueven con fluidez. Esto muestra con datos reales que un grupo no equivale a una congestión. Hacia los 10 s el grupo se desplaza a la barrera y a los 60 s quedan 60 agentes frente al paso principal.")
fig(f"{CAP}/fig_evolucion_S3.png", 16.5, "Figura 5.4-2. Evolución de los grupos en S3 (semilla 42) a los 1, 10, 20 y 60 s")
P("La Figura 5.4-3 muestra el tamaño del grupo principal y la velocidad media de sus miembros. En S1 el grupo se forma (hasta 35 agentes), se disuelve y su velocidad vuelve a 1,2 m/s, es decir, el flujo se recupera. En S2 y S3 el grupo principal se reduce hasta 60 agentes y se queda en ese tamaño, con velocidad media casi nula (cerca de 0,00 m/s en S2 desde los 30 s y 0,02 m/s en S3 a los 60 s). Un mismo grupo puede ser flujo o bloqueo, y solo la velocidad lo distingue.")
fig(f"{CAP}/fig_grupo_principal_tiempo.png", 15.5, "Figura 5.4-3. Tamaño del grupo principal y velocidad media de sus miembros (semilla 42)")
P("Observaciones sobre la calibración:")
r_s3 = df[(df.escenario == "S3")]
B(f"Efecto de ε. Un ε pequeño (0,8 m) deja más agentes como ruido ({c(d('S3',0.8,5).ruido_pct,0)} % en S3 y {c(d('S1',0.8,5).ruido_pct,0)} % en S1 con min_samples = 5) y fragmenta los grupos. Un ε grande (2,0 m) casi elimina el ruido ({c(d('S3',2.0,5).ruido_pct,1)} % en S3), pero junta grupos que con 1,2 m se mantienen separados: el promedio de grupos en S2 baja de {c(d('S2',1.2,5).clusters_prom)} a {c(d('S2',2.0,5).clusters_prom)}. La Figura 5.4-4 lo ilustra: con ε = 2,0 m el grupo principal pasa de 92 a 100 agentes al incorporar agentes más dispersos.")
B(f"Efecto de min_samples. Con ε = 1,2 m en S3, subir min_samples de 3 a 8 aumenta el ruido de {c(d('S3',1.2,3).ruido_pct,1)} % a {c(d('S3',1.2,8).ruido_pct,0)} % y el Silhouette baja de {c(d('S3',1.2,3).silhouette,2)} a {c(d('S3',1.2,8).silhouette,2)}. Valores bajos (3 o 4) aceptan grupos de muy pocos agentes, que pueden ser coincidencias.")
B(f"Silhouette. Crece con ε (de {c(d('S3',0.8,5).silhouette,2)} con 0,8 m a {c(d('S3',2.0,5).silhouette,2)} con 2,0 m en S3), pero eso se debe a que quedan menos grupos y más grandes, no a que la detección sea mejor para el objetivo del proyecto. Por eso no se usó como único criterio.")
fig(f"{CAP}/fig_efecto_eps.png", 15, "Figura 5.4-4. Efecto de ε sobre el mismo instante de S3 (t = 20 s, min_samples = 5)")

H("5.4.6. Calidad del agrupamiento")
P(f"Con los valores iniciales, el Silhouette promedio fue {c(a.silhouette,2)} en S1, {c(b.silhouette,2)} en S2 y {c(g.silhouette,2)} en S3, y el índice Davies–Bouldin {c(a.davies_bouldin,2)}, {c(b.davies_bouldin,2)} y {c(g.davies_bouldin,2)}. Se calcularon únicamente en los instantes con al menos dos grupos ({int(a.instantes_con_2_clusters)} de {int(a.instantes)} en S1, {int(b.instantes_con_2_clusters)} de {int(b.instantes)} en S2 y {int(g.instantes_con_2_clusters)} de {int(g.instantes)} en S3). Los valores indican grupos moderadamente separados, pero describen la forma geométrica y no si el grupo está bloqueado. La tabla completa con ambos índices está en capturas_dbscan/calibracion_dbscan.csv.")

H("5.4.7. Valores adoptados y limitaciones")
P("Se mantienen ε = 1,2 m y min_samples = 5. Con estos valores el ruido es bajo en S2 y S3 (menos de 4 %; en S1 sube a 32 %, esperable con pocos agentes dispersos), se evita que el grupo principal crezca incorporando agentes dispersos y se conserva el criterio del planteamiento (5 agentes como mínimo). Se descartaron ε = 0,8 m por el ruido y ε = 2,0 m por la fusión de grupos.")
P("Limitaciones: (1) el análisis usa las posiciones del motor con ruta fija; no se evaluó con rutas adaptativas; (2) en S2 y S3 se observó que 60 agentes quedan detenidos frente al paso hasta el final de los 60 s, y en algunas semillas de S1 y S3 quedan más agentes sin llegar a los 60 s; esta situación debe revisarse en la integración para saber si corresponde a congestión real o a un bloqueo del motor; (3) DBSCAN es sensible a ε y min_samples; (4) puede unir grupos distintos por encadenamiento de puntos cercanos; (5) un único ε no describe bien concentraciones de densidades muy diferentes, caso para el cual se propone explorar HDBSCAN como extensión opcional.")
import os
os.makedirs("informe", exist_ok=True)
doc.save("informe/Seccion_5_4_DBSCAN.docx"); print("ok")
