# Item 75 — The month's review, written when the month is complete

Opened 2026-10-10. Rob:

> *"when ledger gets a bank transcript that shows a new moth the moth report ai can then start to generate its
> monthly review of the user account. We only had it produce in front of the user when the agent was connected to
> the cloud. Since the ai agent doesn't call home to a server then the worry that data is getting sent that the user
> didn't give permission to."*

**Points M1–M10 for ruling. No code yet.**

## 1. What is true today (measured 2026-10-10, master)

- **The written review is made when the Reports page opens.** `_rcMonthlyRefreshPreview` calls `_rcMonthlyGenerate`
  for whichever month is selected, AI permitting, and saves the text as `report_text_YYYY-MM`.
- **Nothing writes a review when a month ends.** If the person never opens Reports, no month is reviewed.
- **It reviews half months and overwrites itself.** Opening Reports during October writes an "October" review from
  ten days of records and saves it as October's report. Every later visit writes and saves it again, so the saved
  review is whichever was written last, complete or not. The rule *absence is not zero* is broken here: a half month
  is read as a whole one.
- **Nothing says whether a month is complete.** One account imported through September 30 and another whose records
  stop on September 12 produce the same "September".
- **The privacy reason for waiting is gone.** AI runs only on this computer (item 21: local only), and every call is
  in the AI log (item 62). Writing the review without being asked sends nothing anywhere.
- **Item 64 holds:** every report shows its computed summary with AI on or off. The written part teaches; the voice
  check (R1–R11) applies.

## 2. Points for ruling

**M1. Written when the month is complete, once.**
- When an import commits, by any route (a file, *Get my accounts*, or the Downloads watcher), Groundwork checks
  each month that has no saved review.
- When that month is complete (M2), its review is written once, on this computer.

*Recommended* (Rob's direction).

**M2. Complete means every account has moved past the month.**
- A month is complete when every account that had records in it also has a record dated after it, or the person
  says an account is closed or not needed.
- Until then, Reports shows: *"September's review waits for Superior Savings: its records end September 12."* A
  *Write it anyway* button is there, and a review written that way says which accounts it was missing.

*Recommended.* It is *absence is not zero*, made into a rule.

**M3. Nothing is written for a month in progress.**
- Opening Reports no longer writes or saves a review on its own. It shows the month's summary (item 64).
- The person can still ask for a written look at the current month. That one is labelled *month in progress* and
  is never saved as the month's review.

*Recommended.* It fixes the overwrite in §1.

**M4. A saved review is kept as written, and a newer record is said, never silently written over.**
- When records for a reviewed month arrive later (a late import, or a fix through *Check my records*), the review
  says: *"Written October 2; 4 records for September have arrived or changed since. Write it again?"*
- Writing it again keeps the earlier one in the review's history.

*Recommended.*

**M5. Where it shows: quietly.**
- One line in the dashboard's coming-up list: *"Your September review is ready"*. It opens Reports at September.
- No pop-up, no badge count, no sound (TM6).

*Recommended.*

**M6. It runs only when the machine is free.**
- One review at a time, after the import finishes, never at launch.
- If the AI isn't loaded or can't run on this computer, the summary is saved as the month's review, said as such,
  and the written part can be added later from Reports.

*Recommended* (Rob: spend the machine on the finances).

**M7. The same checks as any report.**
- The voice check and number check (R1–R11) apply.
- A written part that fails is not saved. The summary stands, with *"the written part didn't pass Groundwork's
  checks"*.
- The month's note ("Anything unusual?") can be added before or after, and writing again includes it.

*Recommended.*

**M8. Said plainly in Settings.**
- Under AI features: *"Groundwork writes each month's review on this computer when your records show the month is
  complete. Nothing is sent anywhere. Every request is in the AI log."*
- One switch turns the automatic review off. Reports can still write one on request.

*Recommended.*

**M9. AI off.** The summary is the month's review, saved when the month completes. The dashboard line still
appears. *Recommended* (A10).

**M10. Lines and tests.** Master only. Tests:
- an import into October triggers September's review once, and a second import doesn't repeat it;
- an account whose records stop mid-month holds the review and says which account;
- *Write it anyway* names what's missing;
- opening Reports saves nothing;
- a late record marks the review, and writing again keeps the old one;
- a failed voice check saves the summary only;
- AI off saves the summary;
- the switch turns it off.

*Recommended.*

## 3. Not decided here

- **Weekly or yearly reviews.** Not proposed. The Sunday check-in exists, and a year-end review could follow the
  same rule (complete before written).
- **Sending the review anywhere** (email, print). Not proposed.
