# Item 109 — One clock: the computer's own local date and time

Opened 2026-10-22. Rob, after a sample-household badge and the investment prices read *Oct 23* at 8:30 pm on
Oct 22:

> *"should the date and time read off of the system date and time throughout the program ie bios date and time?"*
> *"Instead of using UTC time?"*
> *"write it, push it build it. We have ran into this issue multiple times now lets fully fix it throughout the
> program."*

**BUILT 2026-10-22 (§6), awaiting acceptance.** Rob's words authorise the build. T1-T8 are what is built, and
each departure is named in §6.

---

## 1. What is true today (measured 2026-10-22 on master `3bc87fe`)

**Two clocks are in use.** Some code reads the computer's local clock (`date.today()`, `datetime.now()`,
`new Date().getDate()`). Other code reads UTC, which in the US is 4-5 hours ahead. So from about 8 pm Eastern (7 pm
in winter) to midnight, UTC is already *tomorrow*, and on the last evening of a month it is already *next month*.

**The server stamps UTC in 147 places:**
- `core/database.py`: 79 column defaults (`default=datetime.utcnow`). That covers every `created_at`, the Historian,
  badges (`earned_at`), the AI log, price dates and more;
- `server.py`: 53 places. Some are moments written (`going_at`, `decided_at`, `user_confirmed_at`, `last_updated`,
  answers' `at`). Some are comparisons with those columns (look-back windows, AI-log retention, the 45-day check).
  One is a day: `today = datetime.utcnow().date()` (`server.py:9290`);
- 12 files in `core/` and `migrate.py`: the engines' `recorded_at`, statements, custody decisions, reimbursement
  closes, and `corrections_kept_since`.

**The page takes a day or month from UTC in 47 places.** It uses `toISOString().slice(0, 10)` or `.slice(0, 7)` in
`static/js/app.js`, starting with `today()` itself (`app.js:108`). After 8 pm Eastern:
- the page's *today* is tomorrow;
- a transaction typed in tonight is dated tomorrow;
- *this month* turns over hours early on the last day.

**`new Date(y, m, 1).toISOString()`** works only west of UTC. East of it, local midnight is the day before in UTC, so
the first of the month becomes the last day of the month before.

**Moments written by the page** (`terms_accepted_at`, `savedAt`, `builtAt`, `generatedAt`, the error log's `ts`) are
UTC with a `Z`.

**Met before, each fixed on its own:**
- the *Corrected on* date showed the UTC day (`PLAN_YEAR_TRACKING.md`);
- the Ledger's day headings parse date strings locally on purpose (`app.js:4117`);
- the greeting works out the hour from the UTC offset by hand (`app.js:2248`);
- today's backup reminder keeps a second, UTC copy of each backup's time, only to compare it with `created_at`
  (`server.py:14777`);
- today: a badge and the investment prices dated *Oct 23* on the evening of Oct 22.

**Nothing stops it coming back.** Each fix covered one place.

## 2. What it does

There is **one clock: the computer's own local date and time**. That is the operating system's clock: set from the
hardware clock at start-up, kept right by internet time, and adjusted for daylight saving.
- Every day and month Groundwork works out comes from it: today, this month, a transaction's date, a badge's date,
  what is due.
- Every moment Groundwork records is written in it.
- What was already stored in UTC is converted once, moment by moment, to the same instant in local time. Nothing is
  re-dated, only expressed in the one clock.
- A smoke check fails the build if UTC comes back.

## 3. Points (authorised: Rob 2026-10-22, "write it, push it build it")

**T1. One clock, local.**
- The server writes moments with `datetime.now()`, and days with `date.today()`.
- The page takes days and months from the local calendar (`getFullYear` / `getMonth` / `getDate`), through one helper
  (`_localISODate`). `today()` uses it.

*Recommended.*

**T2. Moments are written in local time.**
- Every `datetime.utcnow()` becomes `datetime.now()`, and `utcfromtimestamp` becomes `fromtimestamp`. That covers the
  79 column defaults too.
- The page writes moments with one helper (`_localStamp`: `YYYY-MM-DDTHH:MM:SS`, local, no `Z`).

*Recommended.*

**T3. What is stored in UTC is converted once.** A migration (`SCHEMA_VERSION` bumped) converts:
- every `DateTime` column written in UTC, each value to the same instant in local time, with the daylight-saving
  offset **of that moment** (a January value moves by 5 hours, a July value by 4);
- the settings that hold UTC moments: `corrections_kept_since`, `narration_last_at`, the yearly-step answers'
  `at`, ask-for-a-tile requests' `at`, saved bank recipes' `saved`, and the dashboard's cached `fetched_at`.

It runs once, under its own flag, and records itself in the Historian (`clock_local`). **Two columns are left as
they are**, because they were never UTC:
- `BillReading.read_at`, written in local time;
- `DebtAccount.paid_off_at`, a day typed on a form.

*Recommended.*

**T4. Append-only records are not rewritten.** The engines' own `recorded_at` stamps (people, reserve, payment plan,
allocation, plan year, classification) are ordered by their sequence numbers, not by time, and an append-only record
is never edited. New entries are written in local time. Earlier entries keep what they recorded. *Recommended.*

**T5. Comparisons follow.** Every comparison with a stored moment uses the same local clock:
- look-back windows, AI-log retention, cache ages and the 45-day check;
- the backup reminder's *added since your last backup*, which uses the backup's local `at` (the extra `utc` copy is
  no longer written; old records keep theirs and nothing reads it).

*Recommended.*

**T6. Date-only strings are read as local days.** A `YYYY-MM-DD` read on the page is a local calendar day, never UTC
midnight. Each place that parses one with `new Date(s)` and shows or compares a day reads it locally.
*Recommended.*

**T7. It can't quietly come back.** A smoke section, s256, fails the build when it finds:
- `utcnow`, `utcfromtimestamp`, or `timezone.utc` in the server, the engines or the migration;
- `toISOString()` used to pick a day or month in the page.

The rare place that genuinely needs UTC (none today) would have to be named in s256 with its reason. *Recommended.*

**T8. Tests (s256).**
- **The conversion:** a planted January moment and a July moment each move by that moment's own offset; the
  settings stamps move the same way; it runs once.
- **Nothing left behind:** the guards in T7.
- **The page's today:** with the clock set to 11:30 pm Eastern on Oct 31, it is Oct 31 and the month is October
  (in Node, where it is available).
- **The backup reminder:** it counts what was added after a backup by the local clock.

*Recommended.*

## 4. Not decided here

- **A person who moves time zone.** Groundwork follows the computer's clock: moments recorded in one zone are read
  as local wall-clock times. A day is what the person's computer said it was when it happened.
- **The 2.0 records' old UTC `recorded_at`** (T4). They are not rewritten. If one is ever shown as a date, it gets
  its own point.

## 6. Built (2026-10-22), awaiting acceptance

**T1 / T2, the server.**
- All 151 UTC stamps in `server.py`, `migrate.py` and 12 files in `core/` now read the local clock, including the 79
  column defaults.
- Four places converted UTC to local by hand for display. They now show what is stored, which is already local:
  - the *Corrected on* date (`core/health_plan.py`);
  - the custody days (`core/bank_versions.py`);
  - a bill account's last download;
  - the AI log's `at`. These two no longer add a `Z`, and neither does the gate-miss log's `ts`.

**T1 / T2 / T6, the page.** `_localISODate()`, `_localStamp()` and `_localDay()` sit beside `today()`.
- All 47 places that took a day or month from `toISOString()` use the local calendar.
- The five moments the page writes use `_localStamp()`.
- A loan's end month, the months since a repayment began, and a certification's expiry read a stored `YYYY-MM-DD` as
  a local day.
- `toISOString()` no longer appears in the page.

**T3, the conversion.**
- `SCHEMA_VERSION` is `20261022-local-clock`, with the migration fingerprint re-pinned (s51) and the schema fixture
  saved (s67).
- `_clock_local_v109` runs first in the migration, in plain SQL on the columns a database has, in one transaction:
  - every `DateTime` column but the two that were never UTC;
  - the T3 settings;
  - a Historian line (`clock_local`, with the count and the offset);
  - the done flag.

  A failure leaves nothing converted, and nothing is converted twice. A new database is only marked.
- **Measured on a real database written today under the old code:** 456 moments moved. The sample badge that read
  *Oct 23* is now *6:24 pm Oct 22*, the evening it was earned.

**T5.** The backup reminder compares each record's `created_at` with the backup's local `at`. New backups no longer
write a `utc` copy (s254 now checks that none is written).

**Tests that planted UTC moments.** Eleven places in `smoke_test.py` and ten smoke sections were simulating the old
clock. They now plant local time, as the app writes it.

**T7 / T8: s256** checks:
- no UTC clock in the server, the engines or the migration. The one place allowed is the converter, which has to say
  UTC; it is named with its reason;
- no `toISOString()` in the page;
- the page's three helpers;
- every column default local;
- each moment moving by its own offset (January -5 h, July -4 h on this computer);
- the settings fields;
- a planted row converted once, and a new database only marked;
- the two never-UTC columns left alone;
- the conversion running first;
- the backup reminder;
- in Node where it is available (CI), 11:30 pm Eastern on Oct 31 reads Oct 31 and October.
