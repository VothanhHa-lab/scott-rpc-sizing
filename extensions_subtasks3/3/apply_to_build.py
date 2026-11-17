"""Applies replacements.md pairs (pairs.py) + new paragraphs + refs to a COPY of the manuscript
in /home/claude/subtasks3/3/build/ and leaves the original untouched."""
import sys, os, shutil, re
sys.path.insert(0, "/home/claude/subtasks3/3")
from pairs import P
B = "/home/claude/subtasks3/3/build/"
if os.path.exists(B): shutil.rmtree(B)
shutil.copytree("/home/claude/urt_v4", B, ignore=shutil.ignore_patterns("*.png", "*.log", "*.aux", "*.out", "*.fls", "*.fdb_latexmk", "m.txt", "manuscript.tex", "manuscript.pdf"))
txt = {f: open(B + f).read() for f in ("manuscript_template.tex", "cover_letter.tex", "OR2.tex")}
for p in P:
    assert txt[p["file"]].count(p["old"]) == 1, p["id"]
    txt[p["file"]] = txt[p["file"]].replace(p["old"], p["new"])
m = txt["manuscript_template.tex"]
# bibliography: add v2 after b31
refs = open("/home/claude/subtasks3/3/refs.tex").read()
v2 = re.search(r"\\bibitem\{v2\}.*", refs).group(0)
m = re.sub(r"(\\bibitem\{b31\}[^\n]*\n)", lambda x: x.group(1) + v2 + "\n", m, count=1)
# 2.3 paragraph after the assumptions paragraph (ends with 'in section~4.6.')
p23 = open("/home/claude/subtasks3/3/section_2_3_paragraph.tex").read()
anchor = "the sizing is repeated with an exact phasor model in section~4.6.\n"
assert m.count(anchor) == 1
m = m.replace(anchor, anchor + "\n" + p23)
# 4.5 paragraph before the subsection 4.6
p45 = open("/home/claude/subtasks3/3/section_4_5_paragraph.tex").read()
anchor = "\\subsection{Sizing with the exact network model and certification of the design}"
assert m.count(anchor) == 1
m = m.replace(anchor, p45 + "\n" + anchor)
txt["manuscript_template.tex"] = m
for f, s in txt.items(): open(B + f, "w").write(s)
# fill (same numbers file as the authors' fill.py, output into build/)
import json
N = json.load(open("/home/claude/code/results/numbers.json"))
s = re.sub(r"\{\{(\w+)\}\}", lambda x: N[x.group(1)], m)
open(B + "manuscript.tex", "w").write(s)
print("built")
