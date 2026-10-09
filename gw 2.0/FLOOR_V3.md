# Item 47 — The necessity floor, version 3 (item 45 H2)

**ACCEPTED and CLOSED (Rob, 2026-10-08: "I accept items 47, 48 and 49"), gate 2566 / 0.** Opened and built 2026-10-08 (Rob: *"build item 45 H2"*). H2 was ruled at design level that day: *"Expand the list to
cover the identified health terms and built-in categories. Test aliases, capitalization, partial matches, and false
positives. A match inside an unrelated word, such as `ER` inside `water`, must not count as valid classification."*
Master only: 1.x never shows a proposed cut, because its builds strip the teaching layer.

## 1. What was wrong (measured 2026-10-08)

`is_protected` matched raw substrings in both directions (`term in name or name in term`). That had two effects.

**It missed common health names:**
- *Medicine, Meds, Rx, Insulin*;
- *Urgent Care, Physician, Pediatrician, Surgery, Ambulance, OB/GYN, Labs*;
- *Hearing Aids, Glasses, Contacts, Optometrist, Orthodontist*;
- the built-in *Long-term Care*;
- and *Electricity, Grocery, Gasoline*.

**It protected unrelated names by accident:**
- *ER* through "water", "groceries" and "therapy";
- *Hospitality* through "hospital", *Doctorate* through "doctor";
- *Parenting* and *Current Expenses* through "rent";
- *Watercolor* through "water", *Transporter* through "transport".

## 2. What was built

- **Whole-word matching.**
  - A name is split into lower-case words, with a plural *s* dropped. A floor term counts when its words appear
    together in the name: *Doctor / Co-pays* has "doctor", *Urgent Care Visit* has "urgent care", *CVS Pharmacy*
    has "pharmacy".
  - A term inside an unrelated word never counts, and a name inside a longer term never counts. In whole words,
    the reverse direction would make the built-in *Home* match "nursing home".
- **The new terms:**
  - medicine, meds, rx, insulin;
  - urgent care, physician, pediatrician, surgery, surgeon, ambulance, ob gyn / obgyn, lab, lab work;
  - vision, eyeglasses, glasses, contacts, contact lenses, optometrist, ophthalmologist, hearing, hearing aid;
  - orthodontist, orthodontics, braces;
  - long term care, home health, nursing home;
  - er, emergency room;
  - electricity, grocery, gasoline, gas.
- **"health" counts only as the whole name.** *Health* is protected; *Health Club*, a gym, is not, as s45 requires.
- **Version 3.** `NECESSITY_FLOOR_VERSION = '3'`, and every verdict carries it.

**Built-in categories:** every one keeps its verdict except two.
- *Long-term Care* is now protected, which is intended.
- *Rental Income*, an income category that is never a lever, no longer matches "rent" inside "rental".

**Known and accepted:** a whole word can still over-protect, as the doctrine allows. *Water Park* is protected, because
"water" is a whole word there. It costs one unavailable lever, never a proposed cut to someone's care.

**Item 46 widens with it.** Its charge-lesson check uses `is_protected` on the category, and on the merchant and
description, so the new names are covered there too.

## 3. Gate

`s159_floor_v3.py`:
- every alias above, in any capitalisation and plural;
- the accidental matches, which must stay false;
- the built-in comparison against version 2's verdicts;
- the version carried in verdicts;
- a mutation (version 2's substring matching protects *ER* and *Hospitality*).

s45's existing near-miss checks (*Television*, *Health Club*) still pass.
