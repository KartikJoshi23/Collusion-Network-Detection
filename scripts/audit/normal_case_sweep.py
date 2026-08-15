"""Every alert on every dataset must resolve to SOMETHING in Case Detail —
either a bundle, or the no-bundle panel. Confirm the API's 404 is the only
'missing' outcome, and count how many alerts land in each band, so we know how
many cases the new panel has to carry."""

import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001/api/v1"


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=90) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return None, str(e)


_, ds = get("/datasets")
problems = []
print(
    f"{'dataset':<20} {'alerts':>7} {'bundle':>7} {'404':>6} {'other':>6}   band split (high/med/low)"
)
for d in ds["datasets"]:
    name = d["dataset"]
    st, payload = get(f"/datasets/{name}/alerts?budget=500")
    rows = payload["alerts"]
    have = miss = other = 0
    hi = md = lo = 0
    for a in rows:
        s = a["risk_score"]
        if s >= 0.6:
            hi += 1
        elif s >= 0.2:
            md += 1
        else:
            lo += 1
        q = urllib.parse.quote(a["alert_id"], safe="")
        code, _ = get(f"/datasets/{name}/explanations/{q}")
        if code == 200:
            have += 1
        elif code == 404:
            miss += 1
        else:
            other += 1
            problems.append(f"{name}: {a['alert_id']} -> HTTP {code}")
    print(f"{name:<20} {len(rows):>7} {have:>7} {miss:>6} {other:>6}   {hi}/{md}/{lo}")

print()
if problems:
    print("UNEXPECTED RESPONSES (anything other than 200 or 404):")
    for p in problems[:20]:
        print("  !!", p)
else:
    print(
        "No unexpected responses: every alert returns either a bundle (200) "
        "or a clean 404 that the no-bundle panel handles."
    )
