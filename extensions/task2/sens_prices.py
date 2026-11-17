import sys, json
sys.path.insert(0, "/home/claude/code")
import analyse as A
s = A.load("base", "/home/claude/code/results")
sc = [("base", {}),
      ("cost 60", dict(cost=60)), ("cost 75", dict(cost=75)), ("cost 100", dict(cost=100)), ("cost 225", dict(cost=225)), ("cost 300", dict(cost=300)),
      ("price 44", dict(price=44)), ("price 126", dict(price=126)), ("price 160", dict(price=160)),
      ("corner low (60, 44)", dict(cost=60, price=44)), ("corner high (225, 126)", dict(cost=225, price=126)),
      ("corner high2 (300, 160)", dict(cost=300, price=160))]
out = []
base_prop = A.methods(s, 750)["proposed"]
for lab, w in sc:
    m = A.methods(s, 750, w)
    p, c = m["proposed"], m["p95"]
    # cost of the base-case design (C=10.44, eps=1) under these weights
    Jb = A.cost_terms(s["design"]["750"]["evals"], base_prop["idx"], w)[0]
    r = dict(case=lab, C=p["C"], eps=p["eps"], J=p["J"], J_p95=c["J"], red=100 * (1 - p["J"] / c["J"]),
             regret_of_base_design=100 * (Jb / p["J"] - 1), loss_share=100 * p["Jloss"] / p["J"], cap_share=100 * p["Jcap"] / p["J"], viol_share=100*p["Jviol"]/p["J"])
    out.append(r)
    print(f"{lab:26s} C*={p['C']:5.2f} eps*={p['eps']:.2f} J={p['J']:6.0f} Jp95={c['J']:6.0f} red={r['red']:4.1f}% regret_base={r['regret_of_base_design']:4.1f}% shares cap/loss/viol={r['cap_share']:.0f}/{r['loss_share']:.0f}/{r['viol_share']:.0f}")
json.dump(out, open("/home/claude/subtasks/2/sens_prices.json", "w"), indent=1)
