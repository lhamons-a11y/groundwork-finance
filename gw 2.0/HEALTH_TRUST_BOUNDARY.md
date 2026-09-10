# The health-data trust boundary

**Gap 12 — the invariant, recorded as doctrine, and measured against what ships today**

> Status: **Doctrine recorded 2026-09-10 (Rob's). Enforcement does not exist, and this document
> does not design it.**
>
> The invariant is stated first and verbatim, because it is the authority; everything after it is
> measurement. **No enforcement mechanism is proposed here** — `HEALTHCARE_FAILURE_SEMANTICS.md`
> §5's closing rule applies with full force: *do not build another safety mechanism merely because
> the design admits that violations exist.* What is needed first is to know where the boundary
> actually is, and the answer turns out to be worth writing down.

---

## 1. The invariant

> **No health-sensitive data may cross the local trust boundary unless the specific operation
> explicitly declares that health data is permitted.**
>
> This is a design blocker, not an advisory guideline. Any operation that could cause
> health-sensitive data to cross the boundary MUST be denied by default unless it has an explicit
> authorization permitting health data.

**Required behaviour**

- Health-sensitive data is **deny-by-default** at the trust boundary.
- Permission to process ordinary data does **not** implicitly permit health data.
- An operation must **explicitly opt into** health-data handling.
- An operation that has not declared health-data permission MUST NOT transmit, export,
  synchronize, log, cache, replicate, serialize, or otherwise move health-sensitive data across
  the boundary.
- The restriction applies **regardless of whether the transfer is intentional or incidental**.
- **Indirect paths count as crossings.** A health-sensitive value embedded inside a larger object,
  metadata structure, error payload, telemetry event, audit record, or diagnostic message is still
  health-sensitive data.
- The system MUST **fail closed** when the health-data permission cannot be determined.
- Adding a new integration, connector, export path, logging path, background job, or serialization
  mechanism MUST NOT **silently inherit** permission to transmit health-sensitive data.

**Blast-radius rule.** A boundary violation is a security-critical blast-radius event, and the
design must make seven things determinable: what could have crossed; which operation permitted or
attempted it; which destinations could receive it; which downstream components could have
observed, retained, logged, cached or replicated it; whether the operation was explicitly
authorized; the earliest point the violation could have occurred; and the maximum plausible scope
of exposure. **The system must not assume a violation affected only the immediate operation.**

**Release-blocking conditions.** Any crossing without explicit health-data authorization;
permission inferred from a broader permission; a failure to determine authorization that results
in transmission; a new data path that bypasses the enforcement point; health-sensitive data
reaching unauthorized logging, telemetry, caching, debugging, analytics or error-reporting
systems; or an inability to determine the downstream blast radius.

**Uniform, not case-by-case.** Violations are not to be solved with individual special cases; the
enforcement model must apply to current and future operations alike.

---

## 2. What the invariant requires structurally

Deny-by-default is a claim about a **place**. It presupposes that crossings pass through a point
where they can be named, checked and refused. Three of the required behaviours are only
satisfiable if such a point exists:

| Requirement | What it presupposes |
|---|---|
| deny-by-default | a place where a crossing is recognisable **as** a crossing |
| fail closed when permission is undeterminable | a place that can be reached without an answer |
| new paths do not silently inherit | a place a new path **must** go through |

So the first question is not *how do we enforce this* but **where are the crossings**. That was
measured rather than assumed.

---

## 3. The measured inventory

*(2026-09-10, against `master` at `eee4e4b`. Excludes `vendor/`, `build/`, `dist/`,
`installer*/`, `.claude/worktrees/`, tests and smoke sections.)*

### Outbound network

| Location | Path |
|---|---|
| `server.py` | ~10 `urlopen` call sites — update check, Ollama tags/chat, model pull, download |
| `price_engine.py`, `gas_price.py`, `utility_price.py`, `flight_price.py`, `trip_distance.py` | one or more each, module-local |
| `launch.py`, `llm_model_eval.py`, `llm_runtime_spike.py` | one or more each |

**Every one opens its own `urllib.request`.** There is no shared egress function, and therefore no
place a crossing can be recognised as one.

### Persistence and replication outside the database

| Location | What it holds |
|---|---|
| `server.py:90` `_log_unhandled` | traceback plus `request.method` and `request.path`, to a persistent file log at INFO |
| `server.py:99` `/api/debug/log-tail` | returns the last 60 log lines over HTTP |
| `server.py:7180` `ai_voice_miss` | appends to `voice_miss_log.jsonl` — including `text`, **the generated sentence, up to 2000 characters** |
| `server.py:4463` `get_llm_miss_log` | reads those entries back and returns the 20 most recent |
| `server.py:6443` `_exports_dir`, `6492` `export_to_file` | file export |
| `server.py:7283`–`7496` | backup create / restore / upload / list |
| `static/js/app.js:1269`+ | the beta bug-report builder |

### The sensitivity layer's actual reach

`core/classification.py` carries the sensitivity machinery — `Sensitivity`, `sensitivity()`,
`DerivedFact` inheritance, and `consume()`'s declared-strength boundary.

**`server.py` imports `core.database`, `core.consequence`, `core.solution`, `core.trophies`,
`core.proactive` and `core.cycles`. It never imports `core.classification`.**

That is the systemic finding, and it is not a defect in either half. The sensitivity layer is
correct and unreached; the crossing points are all older than it. **Gap 12 is not an unstated
invariant over working machinery — it is an invariant whose machinery has no contact with any
crossing that exists.**

---

## 4. Findings

### F1 — there is no enforcement point, and the code has no place to put one

Roughly ten outbound sites in `server.py` and at least eight further modules each opening their
own connection. Nothing distinguishes an egress call from any other function call. The invariant's
*"new paths must not silently inherit permission"* is currently satisfied only in the sense that
**there is no permission to inherit** — every path is its own authority.

### F2 — the bug report's preview is not the payload that leaves

`static/js/app.js`. `openFeedbackModal` renders a section headed **Report preview** containing
`_gwBuildReport(description)`. `_gwSendFeedbackEmail` then rebuilds the same report and **appends a
`SERVER LOG (recent errors)` section** — the last eight `WARNING`/`ERROR`/`CRITICAL` lines fetched
from `/api/debug/log-tail` — before handing it to `mailto:`. `_gwCopyFeedback` appends nothing.

So three artefacts differ: what is previewed, what is copied, and what is sent.

**Stated precisely, because the overstatement is tempting.** This is not silent exfiltration — the
transport is `mailto:`, so the user's mail client opens with the body visible and the user must
send it. What is wrong is narrower and still real: **a panel labelled "Report preview" does not
show the report.** Beside it sits the line *"No account numbers or transaction details are
included"*, which is a claim about content nothing enforces, made about a payload the panel does
not display.

**This is a defect in shipped 1.0 code and is independent of healthcare.** It is the clearest
present instance of the invariant's *indirect paths count as crossings* clause: a server log line
is a diagnostic message, and diagnostic messages are named in the clause explicitly.

### F3 — the narrator's own words are persisted verbatim, outside the sensitivity layer

`ai_voice_miss` writes `text` — the generated sentence, truncated at 2000 characters — to
`voice_miss_log.jsonl`, and `get_llm_miss_log` reads the most recent twenty back out. The route
swallows every failure by design.

Today that file holds sentences about money. **The moment the narrator can speak about a medical
obligation, it holds sentences about health**, in a plain-text file that no part of the sensitivity
machinery knows exists. Nothing in the write path consults `sensitivity()`, because nothing in
`server.py` can.

This is the *replicate* verb in the required-behaviour list, reached by a path nobody would call an
export.

### F4 — the application log is a second such replica, with an HTTP surface

`_log_unhandled` records a traceback with `request.method` and `request.path` for every unhandled
exception, persistently, at INFO. `request.path` is route structure rather than payload — but route
structure over a healthcare module is itself disclosive, and F2 is the path by which those lines
leave the machine.

### F5 — the blast-radius questions are unanswerable today, and one of them structurally

Of the seven, most fail for the same reason: no crossing is recorded as a crossing, so there is no
set to reason over. **Question 7 — the maximum plausible scope of exposure — is the one that fails
structurally rather than incidentally**, because a `mailto:` hands the payload to a mail client
outside the process. Once composed, Groundwork cannot observe whether it was sent, to whom it was
forwarded, or what retained it.

That is worth stating plainly rather than treating as an implementation shortfall: **for at least
one existing path, the maximum plausible scope is not determinable by any amount of instrumentation
on our side.** If the invariant is to hold, that path's *content* must be constrained before it
leaves, because its *destination* cannot be.

---

## 5. Against the release-blocking list

| Condition | Today |
|---|---|
| crossing without explicit authorization | **yes** — no authorization concept exists |
| permission inferred from a broader permission | **not applicable** — no permissions to infer from |
| undeterminable authorization results in transmission | **yes** — the default is transmission |
| a new data path can bypass the enforcement point | **yes** — there is no enforcement point |
| data reaching unauthorized logging / debugging / error reporting | **yes** — F2, F3, F4 |
| blast radius undeterminable | **yes** — F5 |

**Five of six are blocking today.** The healthcare module has not been built, so no *health* data
crosses yet — but every path it would inherit already exists and already carries financial
content. The invariant's own clause is the point: those paths must not silently inherit permission,
and today inheritance is the only mechanism available to them.

---

## 6. What has not been done, deliberately

No enforcement model. No boundary object, no permission type, no decorator, no registry, no
taxonomy of sensitive fields. §5 of `HEALTHCARE_FAILURE_SEMANTICS.md` forbids reaching for a
mechanism at the moment a design admits that violations are possible, and the same trap is
available here in a more attractive form, because a plausible mechanism is easy to picture.

Two things follow that are not mechanism, and are Rob's:

1. **Where is the boundary?** The measurement above assumes it sits at the process edge — network,
   filesystem, clipboard, `mailto:`. Whether the **local browser** is inside or outside it is
   undecided and consequential: `/api/debug/log-tail` is a crossing under one reading and not
   under the other.
2. **What makes a value health-sensitive?** The origin of the record, the domain of the
   classification, or the inference available from it. `core/classification.py` answers this for
   classifications; nothing answers it for a formatted sentence, a route path, or an exception
   message — which is exactly what F2, F3 and F4 are made of.

---

## 7. Decision — the feedback path is not carried into 2.0

*(Rob, 2026-09-10.)* **2.0's beta is closed rather than public, and the in-app bug-report
feature is left out of 2.0 entirely.** The reasoning is that 2.0 is not a program written from
scratch the way 1.0 was — 1.0's major defects were worked through before and after launch — so a
self-service reporting channel is not buying what it bought then.

**What this buys against the invariant, which is more than it looks.** F5 is the finding that a
`mailto:` payload leaves the process for a client Groundwork cannot observe, making question 7 —
maximum plausible scope — undeterminable by any instrumentation on our side. **That path is not
enforced, constrained or instrumented. It is removed.** The one crossing whose blast radius could
not be bounded stops existing, which is the outcome the enforcement discussion was trying to
approximate and could not have reached: a boundary made simpler by subtraction rather than by
mechanism.

**What it does not buy, and the distinction matters more than the win.**

```text
the feature is absent from the code   →  structural
the beta audience is closed           →  policy
```

Only the first is a guarantee of the kind this invariant asks for. A closed audience constrains
*who* could trigger a crossing; it does nothing about deny-by-default, silent inheritance, or
failing closed. **A later session must not read "the beta was closed" as the safeguard** — the
safeguard is that the path is not built.

**And it closes only the egress.** F3 and F4 are replicas, not crossings: `voice_miss_log.jsonl`
still stores the narrator's generated sentence verbatim, and the application log still records
tracebacks with route paths. Removing the report removes the route by which those left the
machine; it leaves both files sitting outside the sensitivity layer, and leaves export, backup and
`/api/debug/log-tail` exactly where they were. **Five of the six release-blocking conditions in §5
still hold.**

**1.x is unaffected by this decision.** The shipped app keeps its report, now print-only
(`a7fc27e`), which is the right answer for a program with a public user base.

---

**One thing is separable and does not wait on either:** F2 is a present defect in shipped code,
small, and fixable on the release line without touching the healthcare design. Fixing it makes the
preview show the payload — it does not make the boundary exist, and must not be mistaken for
having done so.
