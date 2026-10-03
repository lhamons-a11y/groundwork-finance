# The schema pin cannot see the models (item 24)

Opened 2026-10-03 (Rob: *"Open item 24"*). **No code.** Item 24 was named on 2026-09-28 while building item 23. Since
then it has been handled by hand twice: `household_facts` on both lines, each time with an explicit bump and a
one-off upgrade test. Release-blocker class: an upgraded database missing a table or column crashes on first read.

---

## 1. What the pin sees today (measured on master `9c18efc`, lts `b74f7da`)

`migrate.run_migration_if_needed()` skips **everything** while the stored `SCHEMA_VERSION` matches. s51 pins a
fingerprint of `migrate.py`'s code beside the version, so any change to the migration's code fails the gate until the
version is bumped. That catches a new step, or a column added to a `_NEW_*_COLUMNS` list.

**It cannot see `core/database.py`.** Schema changes can arrive there, without touching `migrate.py`, in two ways:

| change | what happens on an upgraded database | caught today? |
|---|---|---|
| **a new model table** | `init_db()`'s `create_all` runs only inside the migration, which is skipped at the same version. A forgotten bump means the table never exists | **no** (handled by hand: item 23 in s129, `household_facts` in s139/s62) |
| **a new column on an existing model**, not added to a `_NEW_*_COLUMNS` list | `create_all` never alters an existing table, so the column never exists - **even with a bump** | **no** |
| a column added to a list, or a new step | the fingerprint moves, and s51 fails until the bump | yes |

**The real upgrade, measured:** a database made by the released **v1.1.0** code (version `20260725-byb`, 23 tables),
upgraded by each line's current migration:

| line | tables expected | missing tables | missing columns |
|---|---|---|---|
| master (2.0) | 51 | 0 | 0 |
| lts/1.x | 24 | 0 | 0 |

So nothing is broken today. The gap is the next change. The second row (an unlisted column) is the more dangerous one,
because **no version check can catch it**. Only upgrading a database that predates the column shows it.

---

## 2. Points for ruling

**P1. Pin the models as the code is pinned.** A second fingerprint, `SCHEMA_MODELS_SHA256`, sits beside
`SCHEMA_VERSION`. It is computed from the models' metadata: every table, and every column's name, type and nullability.
- Any model change (a new table, a new column, a changed type) fails s51 until the version is bumped and both pins are
  updated. The failure prints the new value, as today.
- This catches the forgotten bump for tables, which is the case handled by hand twice.

*Recommended.*

**P2. Upgrade real old databases in the gate.** The repo keeps **schema fixtures**: the exact `CREATE TABLE`
statements a database had at a recorded version, as small text files under `tests/schema/`.
- The gate builds a database from each one, stamps its version, runs today's migration, and fails if any model table
  or column is missing afterwards.
- This is the only check that catches an unlisted column (row 2 above), whatever the version.

*Recommended.*

**P3. Which versions get a fixture.**
- **v1.1.0** (`20260725-byb`, the released 1.x schema) on both lines.
- Then **every version the pin moves from**: each bump commits the fixture of the shape it leaves behind, which is the
  shape existing databases are in.
- A helper script makes the fixture from the previous commit's models, so a bump is: change the models, run the
  helper, bump, update the pins.

*Recommended.*

**P4. Both lines, 1.x first.** It's shared infrastructure, like every gate fix: lts first, then merged to master, with
each line's own fixtures. 1.x has 24 tables and 2.0 has 51. *Recommended.*

**P5. What it does not do.**
- It guards against **forgetting**, not against someone who updates a pin without a bump. That is s51's existing
  stance, stated in its own docstring.
- No migration framework (Alembic and the like). The existing `_add_missing_columns` mechanism stays. The pass adds
  only the two checks.
- It does not rewrite past migrations.

*Recommended.*

## 3. What the tests would have to show

- A model table added without a bump fails s51 (P1).
- A model column added to an existing table but not to its `_NEW_*_COLUMNS` list fails the fixture upgrade (P2), even
  with a bump. This is the mutation that proves P2 can fail.
- A correctly made change (bumped, listed, fixture committed) passes.
- The v1.1.0 fixture upgrades cleanly on both lines, as measured above.

## 4. Ruling (Rob, 2026-10-03)

*"Yes as recommended."* P1–P5 are ruled as recommended. A ruling is not a build authorisation.

## 5. The build (authorised by Rob, 2026-10-03: *"Yes I authorize the build"*)

**P1, the models pinned (s51).**
- `SCHEMA_MODELS_SHA256` sits beside `SCHEMA_VERSION` in `migrate.py`. It is a fingerprint of every model table and
  each column's name, type, nullability and key.
- It is excluded from the code fingerprint like the other pins, so adding it needed no bump: the schema itself did
  not change.
- When the models change, s51 fails and prints four steps: bump; list any new column in its `_NEW_*_COLUMNS` list;
  set the pin; run `schema_fixture.py`.
- **Mutations caught:** a model table added with no bump, and a model column added with no bump.

**P2/P3, real old schemas upgraded (s67).**
- `tests/schema/<version>.sql` holds the exact `CREATE` statements of a database at that version.
- Each fixture is built in **its own process with its own throwaway data folder**, stamped with its version, and
  upgraded by today's migration. Every model table and column must then exist, and the version must be recorded.
- **Mutations caught:**
  - a model column added and bumped but **not listed**, which never reaches an upgraded database. This is the case no
    version check can see;
  - a model table added with no bump.
- s67 also fails if the current `SCHEMA_VERSION` has no fixture.

**`schema_fixture.py`** builds a fresh database with a tree's own migration, in its own process, and saves its schema.
Use `--tree` for another checkout. The v1.1.0 fixture was made from a worktree of the `v1.1.0` tag.

**The fixtures:**

| line | fixtures | what each stands for |
|---|---|---|
| lts/1.x | `20260725-byb` (v1.1.0, 23 tables), `20261002-lts-household-facts` (today, 24) | a 1.1 user's database; today's 1.x |
| master | the same two, plus `20261002-household-facts` (today, 51) | the 1.x fixture on 2.0 is a 1.x user moving to 2.0 |

All of them upgrade cleanly today.

**P4:** lts first (`7d72a70`, gate **903 / 0**), merged to master (`d3afc5e`, gate **2246 / 0**) with 2.0's own
models pin and its current-schema fixture.

**From now on, a schema change is:**
1. change the models;
2. run s51, which prints what to do;
3. bump `SCHEMA_VERSION`, and list any new column;
4. update both pins;
5. run `python schema_fixture.py`.

The old fixtures stay: each is a shape some user's database is in.

## 6. Acceptance (Rob, 2026-10-03)

*"Yes"*. Item 24 is ACCEPTED as built: lts `7d72a70`, master `d3afc5e`.

## 7. Status

ACCEPTED. **Item 24 is CLOSED.**
