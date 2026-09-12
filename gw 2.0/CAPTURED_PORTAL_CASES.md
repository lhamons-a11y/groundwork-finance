# Captured portal — held artefact, or observation with a copy?

> Status: **Case set, 2026-09-12. Evidence mode. No decision, no storage design, no rank.**
> Third fence opened in evidence mode, sitting directly under the acknowledgment ruling. Rob's
> question, and only it:
>
> > **When Groundwork captures an E/servicer portal showing an acknowledgment, what makes that
> > evidence a held artefact versus merely an observation? Does capture itself establish an
> > artefact that can participate in the evidence chain, or does the portal remain an
> > observation even after Groundwork records what it saw?**
>
> **The three dimensions the acknowledgment ruling separated, which the cases must keep apart:**
>
> ```text
> reproducibility   can Groundwork later inspect the same evidence?
> timeliness        when did the evidence represent E's position?
> channel           E · servicer-of-record · live system · user testimony
> ```
>
> **What *held* means, from the Cluster B ruling** — the test each case is run against: a held
> artefact is one Groundwork holds bytes of, so that readings are *of it*: it can be **re-read**
> (a parse dispute is resolvable against it), **retracted** (D6 — everything derived from it can
> be found and withdrawn together), and **found** (D1/D2 — two readings of it are one source).
> An observation has none of these; it enters as testimony.
>
> **Cases vary only the capture condition.** Same portal, same figure, same date.
>
> **Not decided here, by Rob's list:** storage representation; whether screenshots are
> cryptographically trustworthy; resolver ordering; evidence-strength ranks; `remaining`;
> servicing history; whether every capture format is equally reproducible.
>
> **The desired outcome:** whether *captured portal* is a **distinct evidence condition** or
> **merely a storage property** of an observation.

---

## 0. The fixed situation

S's portal, Sept 1, 14:32. It shows *balance $1,925; last payment $175 received Aug 5.* S is
the servicer of record for P's obligation. The channel is therefore *live system of the servicer
of record* in every case below; the as-of is Sept 1 in every case below. **Only what Groundwork
ends up holding varies.**

---

## Case C1 — viewed live, nothing retained, nothing recorded

The household looks at the portal and closes the tab.

- *Held:* nothing. *Recorded:* nothing.
- *In the evidence chain:* **absent.** The observation exists in the household's memory and
  nowhere else. It cannot be re-read, retracted, or found because it was never in the record.
- **Baseline.** Not an observation *in the record*; an observation that never entered it.

## Case C5 — the user reports what the portal showed, no capture

*"The portal showed $1,925 on Sept 1."* Recorded as the user said it.

- *Held:* nothing of the portal. What is held is the **utterance** (D8 — utterances need no
  referent; `recorded_at` separates them).
- *Re-readable:* the utterance, yes; the portal, no. A dispute about what the portal showed
  cannot be resolved against anything — there is nothing to re-read.
- *Retractable:* the utterance, and what was derived from it.
- *Channel:* **user testimony about a live system** — K4/K5's shape. As-of: Sept 1, as the
  user reports it.
- **An observation, in the record as testimony.** This is what *observed* means: the reading
  is held only as someone's report; the thing read is not.

## Case C2 — screenshot or PDF captured and retained

The household captures the page. Groundwork holds the bytes.

- *Held:* an artefact — **but of what?** Not a document S issued. A rendering S's system
  generated on request at 14:32, fixed by the capture. The capture is an artefact **whose
  subject is the observation** — *what the portal displayed at 14:32 on Sept 1.*
- *Re-readable:* yes — the capture. A parse dispute (*$1,925* vs *$1,295*) is resolvable by
  re-reading it. Two readings of the capture are one source (D1/D2 repaired for it).
- *Retractable:* yes — the capture has an identity, and everything derived from it can be found.
- *Channel:* **unchanged — live system of the servicer of record.** Capturing the page did not
  make it S's issued statement; S generated a view, and the household fixed it. The chain to
  E's position runs *capture states X* (held) → *the portal displayed X at 14:32* (asserted:
  the capture is faithful) → *S's position at Sept 1 was X* (the live-system channel) → *P's
  position* (the servicer-of-record link). One link longer than K1 and one link longer than K2.
- *As-of:* Sept 1 14:32 — **now a property of the artefact**, not of the household's memory.
- **Held.** And held on exactly one axis: **reproducibility.** Not on channel; not on timeliness.

> The link *the capture is faithful* is an assertion, and Rob fenced its trustworthiness. It is
> worth noticing that a **scanned mailed statement carries the identical assertion** — bytes
> the household's scanner made, of paper P issued. *Held* has never meant *verified*; it has
> meant *re-readable*. The capture is held in the same sense the scan is.

## Case C3 — portal data imported, original presentation not retained

A connector, or the household typing from the screen, enters `balance=1925, last_payment=175,
as_of=2026-09-01` into Groundwork. The page itself is not kept.

- *Held:* the **values**. Not the artefact.
- *Re-readable:* **no.** The values can be re-*displayed*; nothing can be re-*read*. A parse
  dispute cannot arise (one fixed reading) and cannot be resolved (nothing to read against).
  If `1925` was a transcription of `1295`, the record can never find out from itself.
- *Retractable:* the values, yes. Re-derivable from source: **no** — the source is gone.
- *Channel:* live system, via **the importer's testimony** — *the process asserts the portal
  showed these values.* An exact, timestamped utterance by a process rather than a person.
- **Neither held nor observed as those words have been used — a third state: the *reading* is
  retained, the *referent* is not.** In `DOCUMENT_IDENTITY_CASES.md`'s five distinctions this
  is *which reading* without *which artefact.* It has C2's precision and C5's reproducibility.

**Forces finding 1.** *Held* must mean **the artefact, not the data.** Holding the values buys
exactness and a timestamp; only holding the artefact buys re-reading, retraction-by-identity,
and parse-dispute resolution. A record that treats retained values as *held* has confused a
reading with a referent — the D3 collapse in a new coat.

## Case C4 — the capture is retained; the portal no longer shows it

By October S's portal shows only the current balance; the Sept 1 view is gone from S's side.

- *Held:* the capture, unchanged. Re-readable, retractable, findable — **exactly as in C2.**
- *What changed:* S can no longer be asked *did your portal show $1,925 on Sept 1?* It can
  still be asked *what was the account's position on Sept 1?* — from its ledger.
- *In the chain:* nothing moved. Held-ness is **a property of Groundwork's custody**, not of
  the source's persistence.
- **This is the case that makes capture a condition rather than a convenience.** Without C2's
  capture, the Sept 1 observation is now **unrecoverable by anyone** — C1's state, reached by
  the passage of time. With it, the observation is as inspectable in October as it was in
  September. Capture converts a **perishable** observation into a **durable** one, and the
  difference is not where the bytes sit; it is whether the evidence can ever be examined again.

## Case C6 — captured portal against a later E-held statement, dates controlled

C2's capture: *Sept 1, $1,925.* P's own statement, imported: *dated Sept 15, $1,523* (a second
$175 posted Sept 5).

- *Same as-of?* **No.** Two dated positions, both true, fourteen days apart. Not a conflict —
  finding 4 of the acknowledgment cases (*date first, then channel*) applies before any ranking.
- *Now force the dates equal:* P's statement dated Sept 1 says $1,925; the capture of Sept 1
  says $2,100. **Now a conflict at one as-of.** How is it ordered?
  - By **channel**: P's own issued statement is E speaking as E; the capture is a rendering of
    S's live system — two links further from P. K7's ordering (E's statement > servicer's live
    system) stands.
  - By **reproducibility**: both are held. Equal on this axis. The capture being held does
    **not** lift it past the statement — *held* is not a rank; it is what lets the dispute be
    examined at all.
- **Forces finding 2.** Capture changes **one dimension of three.** Channel and timeliness are
  untouched by it; a captured live-system view is still a live-system view at its as-of. What
  capture buys in C6 is that the conflict is **examinable** — both sides can be re-read — not
  that the captured side wins.

---

## What the cases force

1. **Held means the artefact, not the data** (C3). Retained values are exact and dated and
   cannot be re-read; a retained artefact can. Only the second is *held* in the Cluster B
   sense.
2. **Capture changes exactly one of the three dimensions** (C2, C6): it moves the evidence from
   *observed* to *held* on the **reproducibility** axis, and leaves **channel** (still the live
   system) and **timeliness** (still the as-of of the view) where they were.
3. **Capture is a distinct evidence condition, not a storage property** (C4). The test that
   decides it: an uncaptured observation becomes unrecoverable when the source moves on; a
   captured one does not. That is a difference in what the evidence chain can *do* — re-read,
   retract, resolve — not in where bytes live.
4. **The capture's subject is the observation, not an issued document** (C2). A captured
   portal page is an artefact *of a rendering*; a statement is an artefact P *issued and stands
   behind*. Both are held; they are held **of different things**, and the chain to E's position
   is one assertion longer for the capture.
5. **Held ≠ verified, and this is not special to portals** (C2). A scan of a mailed statement
   carries the same *faithful capture* assertion. The trust question Rob fenced is a question
   about every held artefact the household made, not about screenshots.
6. **There is a middle state — reading retained, referent not** (C3) — and it must not be
   called *held*. It is the importer's exact testimony.

---

## The fence's question, answered by the cases — not ruled

> *Is "captured portal" a distinct evidence condition, or merely a storage property of an
> observation?*

**A distinct evidence condition — on one axis only.** Capture makes the observation
*reproducible*: re-readable, retractable by identity, resolvable in a parse dispute, and durable
past the source's own memory (C4). It does not make the rendering an issued document, does not
change the channel, does not move the as-of, and does not raise the capture past an E-issued
statement in a same-date conflict (C6).

```text
                 reproducibility     channel                       as-of
C1  not recorded       —             —                             —
C5  user report        observed      user testimony · live system  Sept 1 (reported)
C3  values only        exact, not    importer testimony · live     Sept 1 (stamped)
                       re-readable   system
C2  captured           HELD          live system (unchanged)       Sept 1 14:32 (on the artefact)
C4  captured, source   HELD          live system                   Sept 1 14:32
    gone               (unchanged)
K1  E's statement      HELD          E, issued                     statement date
```

The portal **remains a live system** after capture; what Groundwork holds is **an artefact of
having observed it**. Both halves of Rob's question are true at once, on different axes.

---

## What the cases do not establish

1. **Whether every capture format is equally reproducible** — a PDF print, a PNG, a saved HTML
   page, a connector's JSON. Fenced by Rob; C3 shows the boundary case (values without a page)
   and stops.
2. **Whether the capture is faithful.** Finding 5 places the question; it does not answer it.
3. **Any rank.** Finding 2 shows capture does not change channel; K7's channel ordering is used
   as given, not extended.
4. **Whether the capture's as-of is the render time or the portal's own "as of" label**, where
   they differ. The cases assume they agree.
5. **Representation.** Nothing here says how a held-of-a-rendering artefact is stored or how
   its subject is recorded.

---

## Decision remaining — Rob's

Whether to lift the fence on these terms: capture is a distinct evidence condition on the
reproducibility axis alone; *held* means the artefact and never the data; the captured portal
remains live-system channel at its own as-of; and the *faithful-capture* assertion is a
property of every household-made artefact, to be taken up — if ever — as one question rather
than a portal-specific one.
