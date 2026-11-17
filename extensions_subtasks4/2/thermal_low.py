import sys, json
sys.path.insert(0, "/home/claude/subtasks4/2")
import thermal as t
r = t.run(ratings=(10.0, 12.5, 15.0, 17.5, 20.0, 22.5), cooling=("ONAN", "ONAF"), amb=(20.0, 40.0))
json.dump(r, open(t.R_ + "/thermal_low.json", "w"))
