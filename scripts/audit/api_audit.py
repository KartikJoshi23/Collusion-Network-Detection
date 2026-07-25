"""Hit every API surface for every dataset and report anything broken."""

import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001/api/v1"
problems = []
notes = []


def get(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return None, str(e)[:200]


st, domains = get("/domains")
print(f"/domains -> {st}")
print(json.dumps(domains, indent=2)[:400])

st, ds = get("/datasets")
datasets = [d["dataset"] for d in ds["datasets"]]
print(f"\n/datasets -> {st}: {datasets}\n")

for d in ds["datasets"]:
    name = d["dataset"]
    print(f"--- {name} ({d['domain']}) ---")
    st, alerts = get(f"/datasets/{name}/alerts?budget=50")
    if st != 200:
        problems.append(f"{name}: /alerts -> {st} {alerts}")
        print(f"  alerts: FAIL {st}")
        continue
    rows = alerts.get("alerts", alerts if isinstance(alerts, list) else [])
    print(f"  alerts: {len(rows)}")

    st, m = get(f"/datasets/{name}/metrics")
    print(f"  metrics: {st} {'ok' if st == 200 else m}")
    if st != 200:
        problems.append(f"{name}: /metrics -> {st}")

    st, rg = get(f"/datasets/{name}/rigor")
    print(f"  rigor:   {st} {'ok' if st == 200 else rg}")
    if st != 200:
        problems.append(f"{name}: /rigor -> {st}")

    # walk the first 10 alerts: subgraph + explanation
    n_expl, n_missing_expl, n_sub_fail, n_empty_sub = 0, 0, 0, 0
    hollow = 0
    for r in rows[:10]:
        aid = r.get("alert_id")
        q = urllib.parse.quote(aid, safe="")
        st_s, sub = get(f"/datasets/{name}/subgraph/{q}")
        if st_s != 200:
            n_sub_fail += 1
            problems.append(f"{name}: subgraph {aid} -> {st_s}")
        else:
            nn = len(sub.get("nodes", []))
            if nn == 0:
                n_empty_sub += 1
                problems.append(f"{name}: subgraph {aid} EMPTY")
        st_e, ex = get(f"/datasets/{name}/explanations/{q}")
        if st_e == 200:
            n_expl += 1
            b = ex.get("bundle", ex)
            has_motif = bool(b.get("motif"))
            has_flags = bool(b.get("red_flags"))
            fid = b.get("fidelity") or {}
            if not has_motif and not has_flags:
                hollow += 1
        elif st_e == 404:
            n_missing_expl += 1
        else:
            problems.append(f"{name}: explanation {aid} -> {st_e}")
    print(
        f"  first-10 alerts: explanations={n_expl} missing={n_missing_expl} "
        f"subgraph_fail={n_sub_fail} empty_subgraph={n_empty_sub} "
        f"no_motif_and_no_flags={hollow}"
    )
    if n_missing_expl:
        notes.append(f"{name}: {n_missing_expl}/10 top alerts have NO explanation bundle")
    if hollow:
        notes.append(f"{name}: {hollow}/10 top alerts have a bundle but no motif AND no red flags")
    print()

print("=" * 62)
print("HARD PROBLEMS (HTTP errors / empty payloads):")
for p in problems:
    print("  !!", p)
if not problems:
    print("  none")
print()
print("NOTES (working as designed, but user-visible gaps):")
for n in notes:
    print("  -", n)
