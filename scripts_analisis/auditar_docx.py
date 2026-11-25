import docx
import re

doc = docx.Document('informe/2do PArcial IA Final.docx')

print('=== 1. REVISION DE SIMBOLOS LATEX CRUDOS ===')
dolar_matches = []
for i, p in enumerate(doc.paragraphs):
    if '$' in p.text:
        dolar_matches.append((i, p.text.strip()[:80]))
print(f'Total parrafos con signo dolar: {len(dolar_matches)}')
for m in dolar_matches[:10]:
    print(f'  P{m[0]}: {m[1]}')

print('\n=== 2. REVISION DE CODIGO EN MARCO TEORICO (P90-P137) ===')
code_words = ['python', '.py', 'numpy', 'scipy', 'sklearn', 'pygame', 'def ', 'class ', 'import ', 'modulos/', 'configuracion.json', 'agente.', 'entorno.']
found_code_teorico = []
for i in range(90, 138):
    p_text = doc.paragraphs[i].text.lower()
    for w in code_words:
        if w in p_text:
            found_code_teorico.append((i, w, doc.paragraphs[i].text.strip()[:70]))
print(f'Menciones de codigo en Marco Teorico: {len(found_code_teorico)}')
for m in found_code_teorico:
    print(f'  P{m[0]} [{m[1]}]: {m[2]}')

print('\n=== 3. REVISION DE CONCLUSIONES (P414-P424) ===')
for i in range(414, min(425, len(doc.paragraphs))):
    txt = doc.paragraphs[i].text.strip()
    if txt:
        print(f'P{i}: {txt}')

print('\n=== 4. REVISION DE TABLAS DEL DOCUMENTO ===')
print(f'Total tablas: {len(doc.tables)}')
for i, t in enumerate(doc.tables):
    rows = len(t.rows)
    cols = len(t.columns) if rows > 0 else 0
    header = [c.text.strip().replace('\n', ' ') for c in t.rows[0].cells[:4]] if rows > 0 else []
    print(f'Tabla {i}: {rows}x{cols} | Encabezado: {header}')
