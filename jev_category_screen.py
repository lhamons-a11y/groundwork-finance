#!/usr/bin/env python3
"""
JEV CATEGORY SCREEN
===================
Is TypeSafe's Jev worth a slot as a transaction categoriser? A pass/fail screen,
not a score - the same discipline as llm_model_eval.py.

WHAT IS BEING SCREENED
  Jev (api.typesafe.ai, hosted, early access Sept 2026) answers typed questions:
  a `choice` question over a fixed option list returns one option plus a full
  probability distribution and a confidence figure. That shape fits ONE job in
  Groundwork - merchant description -> category - and nothing else the product
  does. This script measures only that job.

THE BASELINE COMES FIRST
  bank_importer.auto_category() already categorises by MCC and keyword. Jev is
  not compared against nothing; it is compared against that. The number that
  matters is not Jev's accuracy but its accuracy ON THE CASES THE BASELINE GETS
  WRONG - the descriptions that fall through to 'Other'. A model that matches
  the keyword table is a slower, dearer, off-device keyword table.

THE CLAIM THAT WOULD JUSTIFY THE HOSTING COST
  Calibration. If confidence 0.95 means right 95% of the time, the product could
  auto-apply high-confidence categories and ask about the rest. If it does not,
  Jev is one more classifier and the hosting cost buys nothing. So the screen
  buckets every answer by stated confidence and reports the hit rate per bucket,
  and it checks that on the GENUINELY ambiguous cases confidence is LOW - a model
  that is 0.97 sure Amazon is Clothing is not calibrated, it is confident.

WHAT LEAVES THIS MACHINE
  Nothing, by default. The corpus below is synthetic - invented merchants and
  national chains, no line from any household's ledger, no amount, no date, no
  card digits. `--dry-run` (the default) prints every request body that WOULD be
  sent and stops. `--send` sends them. The key comes from TYPESAFE_API_KEY and
  is never written anywhere. home_install_import_rules.json and the database are
  never read - they are somebody's real merchants.

DISQUALIFIERS (any one ends the screen regardless of the rest)
  * a category outside the option list (the API promises this cannot happen -
    verify it, do not trust it)
  * confidence >= HIGH on an ambiguous case
  * failing to beat the baseline on its own blind spots (the WORST run, not the mean)
  * changing its answer on identical input more than MAX_FLIP_RATE of the time

USAGE
    python jev_category_screen.py                 # dry run: show requests, exit
    python jev_category_screen.py --send          # run the screen, 3 repeats
    python jev_category_screen.py --send --runs 5
    python jev_category_screen.py --send --out screen.json
Requires TYPESAFE_API_KEY in the environment for --send. No extra pip deps.
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):      # cp1252 console cannot print the report
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from bank_importer import auto_category          # the baseline, unmodified
from core.database import CATEGORY_TREE           # the option list, unmodified

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
HIGH = 0.90          # "auto-apply" confidence - the bar an ambiguous case must stay under
BUCKETS = [(0.0, 0.5), (0.5, 0.8), (0.8, HIGH), (HIGH, 1.01)]
MIN_BUCKET_N = 10    # below this a bucket's hit rate is a number, not a finding
MAX_FLIP_RATE = 0.10 # share of repeat pairs allowed to change answer on identical input

# ── The corpus ───────────────────────────────────────────────────────────────
# (description, direction, truth, kind)
#   direction  'debit' | 'credit' - the only thing sent besides the description
#   truth      a category name, or a tuple of acceptable names
#   kind       'plain'      keyword table should get it; a control, not a test
#              'blindspot'  keyword table falls through to 'Other' or misfires;
#                           THIS is where Jev has to earn its place
#              'ambiguous'  no single right answer from the text alone; the
#                           screen checks that Jev's confidence stays LOW
# Descriptions are in the shape the rich-description parser produces for a
# Superior-CU-style feed (merchant text only, tail stripped). All invented.
CORPUS = [
    # plain - controls
    ("KROGER 0421 MILLBROOK OH",                         "debit",  "Groceries",            "plain"),
    ("SHELL OIL 57442 MILLBROOK OH",               "debit",  "Gas / Fuel",           "plain"),
    ("NETFLIX.COM",                                 "debit",  "Streaming Video",      "plain"),
    ("CVS/PHARMACY #6110",                          "debit",  "Prescriptions",        "plain"),
    ("PLANET FITNESS 555-2201",                     "debit",  "Gym / Fitness",        "plain"),
    ("SPECTRUM 855-707-7328",                       "debit",  ("Internet", "Cable / TV"), "plain"),
    ("MCDONALD'S F14211",                           "debit",  "Fast Food / Takeout",  "plain"),
    ("STARBUCKS STORE 08814",                       "debit",  "Coffee Shops",         "plain"),
    ("STATE FARM INSURANCE",                        "debit",  ("Auto Insurance", "Homeowner's Insurance", "Life Insurance"), "ambiguous"),

    # blind spots - local names the keyword table cannot know
    ("MAPLE ST DINER",                              "debit",  "Restaurants",          "blindspot"),
    ("NORTHSIDE VETERINARY CLINIC",                 "debit",  "Vet / Medical",        "blindspot"),
    ("HANK'S TIRE & LUBE",                          "debit",  "Car Maintenance",      "blindspot"),
    ("RIVERBEND PEDIATRICS",                        "debit",  "Doctor / Co-pays",     "blindspot"),
    ("DR PATEL FAMILY DENTISTRY",                   "debit",  "Dental",               "blindspot"),
    ("HOLLIS CO WATER & SEWER",                      "debit",  "Water / Sewer",        "blindspot"),
    ("REPUBLIC SERVICES 419",                       "debit",  "Trash",                "blindspot"),
    ("LITTLE SPROUTS DAYCARE",                      "debit",  "Childcare / Daycare",  "blindspot"),
    ("SHAWNEE LAWN CARE LLC",                       "debit",  "Lawn / Landscaping",   "blindspot"),
    ("ADT SECURITY SVCS",                           "debit",  "Security System",      "blindspot"),
    ("BOB EVANS #0221",                             "debit",  "Restaurants",          "blindspot"),
    ("MEIJER FUEL 233",                             "debit",  "Gas / Fuel",           "blindspot"),
    ("CLEAR VISION OPTICAL",                        "debit",  "Vision",               "blindspot"),
    ("FIRST BAPTIST CHURCH",                        "debit",  "Charitable Donations", "blindspot"),
    ("ROVER.COM PET SITTING",                       "debit",  "Boarding / Pet Sitting","blindspot"),
    ("PAWS & CLAWS GROOMING",                       "debit",  "Grooming",             "blindspot"),
    ("OHIO STATE UNIV BURSAR",                      "debit",  "Tuition / Courses",    "blindspot"),
    ("CAPITAL ONE ONLINE PMT",                      "debit",  "Debt",                 "blindspot"),
    ("ZELLE TO SAVINGS",                            "debit",  "Transfer",             "blindspot"),
    ("VENMO CASHOUT",                               "credit", ("Transfer", "Side Income"), "ambiguous"),
    ("ACME PLUMBING & HEATING",                     "debit",  "Home Maintenance",     "blindspot"),
    ("WESTGATE LANES BOWLING",                      "debit",  "Activities / Events",  "blindspot"),
    ("PIANO LESSONS - M HARTMAN",                   "debit",  "Kids Activities",      "blindspot"),
    ("ADOBE *CREATIVE CLOUD",                       "debit",  "Software / Apps",      "blindspot"),
    ("COSTCO WHSE #1140",                           "debit",  ("Groceries", "Household Supplies"), "ambiguous"),
    ("AMAZON MKTPL*2K4T91",                         "debit",  ("Clothing", "Household Supplies", "Other"), "ambiguous"),
    ("WALMART SUPERCENTER 2287",                    "debit",  ("Groceries", "Household Supplies"), "ambiguous"),
    ("SQ *THE CORNER MARKET",                       "debit",  ("Groceries", "Restaurants", "Coffee Shops"), "ambiguous"),
    ("PAYROLL DEP - MIDWEST PACKAGING",             "credit", "Paycheck / Salary",    "blindspot"),
    ("IRS TREAS 310 TAX REF",                       "credit", ("Side Income", "Other"), "ambiguous"),
    ("INTEREST PAID",                               "credit", ("Side Income", "Interest / Fees"), "ambiguous"),
]

assert len(CORPUS) >= 30, "a screen under 30 cases cannot carry a verdict"


# ── Options: the category tree as Jev choice criteria ────────────────────────
def _slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_options():
    """Leaf categories, plus parents that have no children (Transfer, Debt...).
    Choosing a bare parent when a leaf exists is a non-answer, so parents with
    children are excluded from the option list."""
    parents_with_children = {p for (_n, _t, _c, _i, p, *_r) in CATEGORY_TREE if p}
    options, names = {}, {}
    for (name, ctype, _c, _i, parent, *_r) in CATEGORY_TREE:
        if name in parents_with_children:
            continue
        key = _slug(name)
        desc = f"{name} ({parent})" if parent else name
        if ctype == "income":
            desc += " - money coming in"
        options[key] = desc
        names[key] = name
    assert len(options) <= 255, "Jev choice cardinality is 255"
    return options, names


OPTIONS, KEY_TO_NAME = build_options()
NAME_SET = set(KEY_TO_NAME.values())
PARENT_OF = {n: p for (n, _t, _c, _i, p, *_r) in CATEGORY_TREE}
for _d, _dir, truth, _k in CORPUS:
    for t in (truth if isinstance(truth, tuple) else (truth,)):
        assert t in NAME_SET, f"corpus truth not in option list: {t!r}"


# ── Requests ─────────────────────────────────────────────────────────────────
def request_body(description, direction):
    return {
        "model": MODEL,
        "state": {"description": description, "direction": direction},
        "questions": {
            "category": {
                "type": "choice",
                "instructions": (
                    "`description` is the merchant text from a bank transaction; "
                    "`direction` says whether money left (debit) or arrived (credit). "
                    "Which household budget category does this transaction belong to?"
                ),
                "criteria": OPTIONS,
            }
        },
    }


def send(body, key):
    data = json.dumps(body).encode()
    req = urllib.request.Request(ENDPOINT, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    return res, (time.perf_counter() - t0) * 1000


# ── Scoring ──────────────────────────────────────────────────────────────────
def accepts(truth, name, coarse=False):
    """coarse=True also accepts the truth's parent - the keyword table answers
    'Income' where the option list only offers 'Paycheck / Salary'. Jev is
    never scored coarsely; it was given the leaves."""
    truths = truth if isinstance(truth, tuple) else (truth,)
    if coarse:
        truths = truths + tuple(PARENT_OF[t] for t in truths if PARENT_OF.get(t))
    return name in truths


def bucket_of(conf):
    for lo, hi in BUCKETS:
        if lo <= conf < hi:
            return f"[{lo:.2f},{min(hi, 1.0):.2f})"
    return "?"


def baseline_pass(runs_out):
    print("\n── BASELINE  bank_importer.auto_category (no MCC - description only)")
    hits, blind_hits, blind_n = 0, 0, 0
    for desc, _dir, truth, kind in CORPUS:
        got = auto_category(desc)
        ok = accepts(truth, got, coarse=True)
        hits += ok
        if kind == "blindspot":
            blind_n += 1
            blind_hits += ok
        runs_out[desc]["baseline"] = got
        flag = "  " if ok else "✗ "
        print(f"  {flag}{desc:<38} -> {got:<24} truth={truth}")
    n = len(CORPUS)
    print(f"  overall {hits}/{n} = {hits/n:.0%}   blind spots {blind_hits}/{blind_n} = {blind_hits/blind_n:.0%}")
    return hits, blind_hits, blind_n


def screen(runs, key, out_path):
    per_case = defaultdict(dict)
    b_hits, b_blind_hits, blind_n = baseline_pass(per_case)

    print(f"\n── JEV  {MODEL} · {runs} runs x {len(CORPUS)} cases")
    disq = []
    lat, cost_in, cost_out = [], 0, 0
    by_bucket = defaultdict(lambda: [0, 0])          # bucket -> [hits, n]
    run_hits, run_blind_hits = [], []
    flips = 0
    amb_high = []

    for run in range(runs):
        hits, blind_hits = 0, 0
        for desc, direction, truth, kind in CORPUS:
            body = request_body(desc, direction)
            try:
                res, ms = send(body, key)
            except urllib.error.HTTPError as e:
                print(f"    HTTP {e.code} on {desc!r}: {e.read()[:200]!r} - skipping")
                continue
            except Exception as e:
                print(f"    call failed ({type(e).__name__}) on {desc!r} - skipping")
                continue
            lat.append(ms)
            usage = res.get("usage") or {}
            cost_in += usage.get("input_tokens", 0)
            cost_out += usage.get("output_tokens", 0)

            ans = (res.get("answers") or {}).get("category") or {}
            choice_key = ans.get("choice")
            conf = float(ans.get("confidence", 0.0))
            name = KEY_TO_NAME.get(choice_key)
            if name is None:
                # The API promises answers inside the schema. Check it anyway;
                # a promise is not a measurement.
                disq.append(f"out-of-schema answer {choice_key!r} for {desc!r}")
                continue

            ok = accepts(truth, name)
            hits += ok
            if kind == "blindspot":
                blind_hits += ok
            if kind != "ambiguous":
                b = bucket_of(conf)
                by_bucket[b][0] += ok
                by_bucket[b][1] += 1
            elif conf >= HIGH:
                amb_high.append((desc, name, conf))

            prev = per_case[desc].get("jev")
            if prev is not None and prev[0] != name:
                flips += 1
            per_case[desc]["jev"] = (name, conf)
            per_case[desc].setdefault("runs", []).append(
                {"run": run, "choice": name, "confidence": conf, "ok": ok, "ms": round(ms)})
            if run == 0:
                flag = "  " if ok else "✗ "
                print(f"  {flag}{desc:<38} -> {name:<24} conf={conf:.2f}  {ms:5.0f}ms  [{kind}]")
        run_hits.append(hits)
        run_blind_hits.append(blind_hits)

    n = len(CORPUS)
    print("\n── RESULTS")
    print(f"  per-run overall     {run_hits}  ({', '.join(f'{h/n:.0%}' for h in run_hits)})")
    print(f"  per-run blind spots {run_blind_hits} of {blind_n}  ({', '.join(f'{h/blind_n:.0%}' for h in run_blind_hits)})")
    print(f"  baseline            overall {b_hits}/{n}   blind spots {b_blind_hits}/{blind_n}")
    if runs > 1:
        print(f"  answer flips across runs: {flips}  (a categoriser that changes its mind on identical input is a coin flip)")
    if lat:
        print(f"  latency  median {statistics.median(lat):.0f}ms  p95 {sorted(lat)[int(0.95*len(lat))-1]:.0f}ms  "
              f"(ollama phi3.5 narration for comparison: seconds)")
    print(f"  tokens   in {cost_in}  out {cost_out}  ->  ${cost_in * 0.042 / 1e6:.4f} at $0.042/MTok input, output free")

    print("\n── CALIBRATION (non-ambiguous cases only; read n before the rate)")
    for lo, hi in BUCKETS:
        b = f"[{lo:.2f},{min(hi, 1.0):.2f})"
        h, m = by_bucket.get(b, [0, 0])
        if m == 0:
            print(f"  {b}  n=0")
            continue
        rate = h / m
        verdict = "n too small" if m < MIN_BUCKET_N else (
            "calibrated" if lo <= rate <= min(hi, 1.0) + 0.05 else "NOT calibrated")
        print(f"  {b}  n={m:<3} hit rate {rate:.0%}   {verdict}")

    if amb_high:
        print(f"\n  ambiguous cases answered at >= {HIGH:.2f} confidence ({len(amb_high)}):")
        for desc, name, conf in amb_high:
            print(f"    {desc:<38} -> {name}  conf={conf:.2f}")
        disq.append(f"{len(amb_high)} ambiguous case(s) at confidence >= {HIGH} - confident, not calibrated")

    if runs > 1:
        pairs = len(CORPUS) * (runs - 1)
        if flips / pairs > MAX_FLIP_RATE:
            disq.append(f"{flips}/{pairs} repeat pairs changed answer ({flips/pairs:.0%} > {MAX_FLIP_RATE:.0%})")

    # The blind-spot bar: the WORST run must beat the baseline, not the mean.
    if run_blind_hits and min(run_blind_hits) <= b_blind_hits:
        disq.append(f"worst run's blind-spot hits ({min(run_blind_hits)}) do not beat baseline ({b_blind_hits})")

    print("\n── VERDICT")
    if disq:
        print("  FAIL")
        for d in disq:
            print(f"    - {d}")
    else:
        print("  PASS the screen. That is a permission to keep looking, not a decision:")
        print("    the hosting question (a second off-device path) is not measured here and is Rob's.")

    if out_path:
        Path(out_path).write_text(json.dumps({
            "model": MODEL, "runs": runs, "corpus_n": n,
            "baseline": {"overall": b_hits, "blind": b_blind_hits, "blind_n": blind_n},
            "jev": {"overall_per_run": run_hits, "blind_per_run": run_blind_hits, "flips": flips},
            "latency_ms": lat, "tokens": {"in": cost_in, "out": cost_out},
            "buckets": {b: v for b, v in by_bucket.items()},
            "disqualifiers": disq,
            "cases": {d: v for d, v in per_case.items()},
        }, indent=2))
        print(f"\n  written {out_path}")


def dry_run():
    print("DRY RUN - nothing sent. This is every request body that --send would post.\n")
    body = request_body(*CORPUS[0][:2])
    print(json.dumps(body, indent=2))
    print(f"\n... and {len(CORPUS) - 1} more, identical except `state`. The `state` values:\n")
    for desc, direction, _t, kind in CORPUS:
        print(f"  {direction:<7} {desc:<38} [{kind}]")
    print(f"\n{len(OPTIONS)} options in the choice list (cardinality limit 255).")
    print("Baseline on this corpus, for reference:")
    baseline_pass(defaultdict(dict))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--send", action="store_true", help="actually call the API (default: dry run)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", help="write a JSON record of the screen")
    a = ap.parse_args()
    if not a.send:
        dry_run()
        return
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit("TYPESAFE_API_KEY not set; nothing sent.")
    screen(a.runs, key, a.out)


if __name__ == "__main__":
    main()
