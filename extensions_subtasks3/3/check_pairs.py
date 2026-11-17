import sys, json
sys.path.insert(0, "/home/claude/subtasks3/3")
from pairs import P
base = "/home/claude/urt_v4/"
ok = True
for p in P:
    s = open(base + p["file"]).read()
    n = s.count(p["old"])
    print(p["id"], p["file"], "occurrences of old:", n)
    if n != 1: ok = False
print("ALL UNIQUE" if ok else "PROBLEM")
