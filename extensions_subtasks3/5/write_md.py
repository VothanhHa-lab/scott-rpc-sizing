import json
R = json.load(open("/home/claude/subtasks3/5/replacements.json"))
out = ["# Replacements (exact OLD -> NEW), sub-task 5\n",
       "Every OLD string occurs exactly once in its file (checked by make_replacements.py). Files: /home/claude/urt_v4/manuscript_template.tex, OR2.tex, cover_letter.tex.",
       "`{{key}}` placeholders are kept wherever the old text used them; all other new numbers come from decomposition.json.",
       "`apply_test.py` applies all pairs to copies and compiles them (done: manuscript 34 pages, OR2 13 pages, cover letter 1 page, no new warnings).\n",
       "Additional one-line change in fill.py (Table A is generated, its last row label lives in numbers.json):\n",
       "```python\nN['TABLE_A'] = N['TABLE_A'].replace('Expected annual cost $J$', 'Annual objective $J$')   # insert after N = json.load(...)\n```\n",
       "New table block for Table tEx = replacement no. %d; new table tDec is inserted by replacement no. %d.\n" % (
           [r['id'] for r in R if r['where'].startswith('Table tEx')][0], [r['id'] for r in R if 'Table tDec' in r['where']][0])]
for r in R:
    out.append(f"## R{r['id']}. {r['file']} - {r['where']}\n")
    if r["note"]:
        out.append(f"_Note: {r['note']}_\n")
    out.append("OLD:\n```latex\n" + r["old"] + "\n```\n")
    out.append("NEW:\n```latex\n" + r["new"] + "\n```\n")
open("/home/claude/subtasks3/5/replacements.md", "w").write("\n".join(out))
print(len(R))
