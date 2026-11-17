import json, re, shutil, os, subprocess
B = "/home/claude/subtasks3/5/build/"
os.makedirs(B, exist_ok=True)
R = json.load(open("/home/claude/subtasks3/5/replacements.json"))
src = "/home/claude/urt_v4/"
txt = {f: open(src + f).read() for f in ("manuscript_template.tex", "OR2.tex", "cover_letter.tex")}
for r in R:
    assert txt[r["file"]].count(r["old"]) == 1, r["where"]
    txt[r["file"]] = txt[r["file"]].replace(r["old"], r["new"])
for f, t in txt.items():
    open(B + f, "w").write(t)
# fill as fill.py does
N = json.load(open("/home/claude/code/results/numbers.json"))
N['TABLE_A'] = N['TABLE_A'].replace('Expected annual cost $J$', 'Annual objective $J$')
s = txt["manuscript_template.tex"]
missing = sorted(set(k for k in re.findall(r"\{\{(\w+)\}\}", s) if k not in N)); assert not missing, missing
open(B + "manuscript.tex", "w").write(re.sub(r"\{\{(\w+)\}\}", lambda m: N[m.group(1)], s))
for f in os.listdir(src):
    if f.endswith(".pdf") and f.startswith(("fig", "orcid")) or f.endswith(".tex") and f.startswith("appendix"):
        if not os.path.exists(B + f): shutil.copy(src + f, B + f)
print("ok")
