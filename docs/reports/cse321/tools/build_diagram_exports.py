#!/usr/bin/env python3
"""Build sibling DOT layouts for report SVGs; Mermaid remains editable source.

These exports depict the same components/dependencies as the Mermaid sources;
they are Graphviz layouts, not a claimed direct Mermaid render.
"""
from pathlib import Path
import html
D = Path(__file__).resolve().parents[1]/'diagrams'
architecture = {
'B': 'Staff browser', 'R':'Django middleware + URL routing\nSession authentication / CSRF',
'V':'Native staff views\ncore/views.py', 'A':'Django Admin\nGradeAdmin + academic configuration',
'F':'Forms + write functions\ngrade_editor / student_intake',
'C':'Calculation functions\nLO → course PO → student PO',
'T':'Django templates\nHTML + evidence explanations',
'H':'Grade history functions\nSupported grade writes only',
'O':'Django ORM\nQueries + transactions',
'D':'Local SQLite database\n15 core tables + auth/session/admin tables'}
edges = [('B','R'),('R','V'),('R','A'),('V','F'),('V','C'),('V','T'),('T','B'),
         ('F','H'),('A','H'),('F','O'),('A','O'),('H','O'),('C','O'),('V','O'),('O','D')]
def q(s):
    import json
    return json.dumps(s, ensure_ascii=False)
s = ['digraph G {', 'graph [rankdir=TB, bgcolor="white", pad=0.25, nodesep=0.4, ranksep=0.55, fontname="Helvetica", fontsize=18, label="Gnosis v0.1 — application components", labelloc=t];',
     'node [shape=box, style="rounded,filled", fillcolor="#eef3f8", color="#17324d", fontname="Helvetica", fontsize=15, margin="0.18,0.14"];',
     'edge [color="#64748b", arrowsize=0.7];']
s += [f'{k} [label={q(v)}];' for k,v in architecture.items()]
s += [f'{a} -> {b};' for a,b in edges]
s += ['{rank=same; V; A;}', '{rank=same; F; C; T;}', '}']
(D/'architecture.dot').write_text('\n'.join(s)+'\n')
classes = {
'Form': ('Django framework', []),
'EnrollmentGradeForm': ('Form subclass', ['revision', '__init__(assessments, grades)', 'clean()']),
'ModelAdmin': ('Django framework', []),
'GradeAdmin': ('ModelAdmin subclass', ['get_readonly_fields()', 'save_model()', 'delete_model()', 'delete_queryset()']),
'Grade': ('Django model', ['score', 'clean()', 'save()']),
'Assessment': ('Django model', ['max_score', 'course_grade_weight']),
'Enrollment': ('Django model', ['status']),
'CourseOffering': ('Django model', ['clean()', 'save()']),
'LogEntry': ('Django admin model', ['change_message', 'action_time'])}
s = ['digraph G {', 'graph [rankdir=TB, bgcolor="white", pad=0.3, nodesep=0.55, ranksep=0.65, fontname="Helvetica", fontsize=18, label="Gnosis — grading classes and responsibilities\\nSelected workflow classes; the complete relational model is documented separately", labelloc=t];',
     'node [shape=plain, fontname="Helvetica", fontsize=14];',
     'edge [fontname="Helvetica", fontsize=11, color="#64748b", arrowsize=0.7];']
for name, (kind, members) in classes.items():
    rows = f'<TR><TD BGCOLOR="#17324d"><FONT COLOR="white"><B>{name}</B></FONT></TD></TR><TR><TD BGCOLOR="#e2e8f0">{kind}</TD></TR>'
    rows += ''.join(f'<TR><TD ALIGN="LEFT">{html.escape(m)}</TD></TR>' for m in members)
    s.append(f'{name} [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">{rows}</TABLE>>];')
for child,parent in [('EnrollmentGradeForm','Form'),('GradeAdmin','ModelAdmin')]:
    s.append(f'{child} -> {parent} [arrowhead=empty, label="inherits", constraint=false];')
for a,b,label in [('EnrollmentGradeForm','Assessment','field bounds'),('EnrollmentGradeForm','Grade','initial values'),('GradeAdmin','Grade','save/delete'),('GradeAdmin','LogEntry','via history functions')]:
    s.append(f'{a} -> {b} [style=dashed, label={q(label)}];')
for a,b,label in [('Grade','Assessment','assessment'),('Grade','Enrollment','enrollment'),('Assessment','CourseOffering','offering'),('Enrollment','CourseOffering','offering')]:
    s.append(f'{a} -> {b} [label={q(label)}, taillabel="0..*", headlabel="1", labeldistance=2];')
s += ['{rank=same; Form; EnrollmentGradeForm; ModelAdmin; GradeAdmin;}', '{rank=same; Grade; LogEntry;}', '{rank=same; Assessment; Enrollment;}', '}']
(D/'grading-classes.dot').write_text('\n'.join(s)+'\n')
