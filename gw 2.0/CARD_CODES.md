# Item 55 — The card codes name the same categories as the words

Opened 2026-10-09 (Rob: *"open the card-code drift as an item"*). It was found while building item 54
(`MATCHER_ONE_ANSWER.md`), which left the card-code maps unchanged. It builds on item 54's branch. **RULED 2026-10-09 (Rob: "approve C1–C6 as
recommended")**: master only, with item 54 (C6). **BUILT 2026-10-09 (Rob: "build item 55")**: the 49 codes in §1 changed in `MCC_CATEGORY_MAP`, `CLIENT_MCC_CATEGORY_MAP` written from it, a code naming Other lets the words decide on both sides (C4), Personal Care and Tuition / Courses join the review's old answers (C5), `s167`. Three codes listed twice with the same value (5732, 8398, 8351) now appear once. Awaiting acceptance.

## 1. What is true today (measured 2026-10-09 on item 54's branch, 3e48033)

A card purchase can carry a merchant category code (MCC), a four-digit code for the kind of business. When it does,
the code decides the category before any words are read (`auto_category`: *"MCC (definitive) takes priority"*).
There are two copies of the code table: `MCC_CATEGORY_MAP` on the server and `CLIENT_MCC_CATEGORY_MAP` on the page.

- **Both list the same 121 codes.** They agree on 78 and disagree on 43.
- **6 of the agreeing codes name a parent** (Transportation): 5552 EV charging, 4111 commuter transport, 4121
  taxis and rideshare, 4131 bus lines, 4789 transport services, 7523 parking lots.
- **On the 43 they disagree on, the server always names a parent** (Utilities, Healthcare, Insurance, Subscriptions,
  Personal, Entertainment, Education) or Property Taxes. The page names a leaf, sometimes the wrong one.

| Codes | Kind of business | Server | Page | Would name |
|---|---|---|---|---|
| 4900, 4901 | electric, gas, water and sanitary utilities | Utilities | Electric | no guess (C3) |
| 5552 | EV charging | Transportation | Transportation | Gas / Fuel |
| 4111, 4121, 4131, 4789 | commuter transport, taxis and rideshare, bus lines, transport services | Transportation | Transportation | Rideshare / Transit |
| 7523 | parking lots | Transportation | Transportation | Parking / Tolls |
| 5912, 5122 | pharmacies, drug sellers | Healthcare | Doctor / Co-pays | Prescriptions |
| 8021 | dentists and orthodontists | Healthcare | Doctor / Co-pays | Dental |
| 8042 | optometrists | Healthcare | Doctor / Co-pays | Vision |
| 8011, 8031, 8041, 8050, 8062, 8071, 8099, 5047 | doctors, chiropractors, nursing care, hospitals, labs, medical services and equipment | Healthcare | Doctor / Co-pays | Doctor / Co-pays |
| 5960, 6300, 6381 | insurance (5960 is direct-marketing insurance; Nationwide Pet in the tuning data) | Insurance | **Health Insurance** | no guess (C3) |
| 5734, 5818, 7372 | software stores, digital goods, data processing | Subscriptions | Other Subscriptions | Software / Apps |
| 5968 | subscription merchants | Subscriptions | Other Subscriptions | Other Subscriptions |
| 4816 | network and information services (internet providers and online services) | Subscriptions | Other Subscriptions | no guess (C3) |
| 8999 | professional services (Experian in the tuning data) | Subscriptions | Other Subscriptions | no guess (C3) |
| 5621, 5651, 5661, 5691 | clothing and shoe stores | Personal | Personal Care | Clothing |
| 5921 | package stores (beer, wine, liquor) | Personal | Personal Care | no leaf (C3) |
| 7832, 7922, 7929, 7991, 7993, 7994, 7996 | cinemas, ticket agencies, bands, attractions, arcades, amusement parks | Entertainment | Activities / Events | Activities / Events |
| 8211 | elementary and secondary schools | Education | Tuition / Courses | School / Tuition |
| 8220, 8241, 8244, 8249, 8299 | colleges, correspondence, business, trade and other schools | Education | Tuition / Courses | Tuition / Courses |
| 8351 | child care | Education | **Tuition / Courses** | Childcare / Daycare |
| 9311 | tax payments | Property Taxes | Interest / Fees | no leaf (item 54 M5) |

### What it breaks

- **The server saves parents** for 49 codes, which breaks the app's own rule that a transaction never gets a parent.
  It's the card-code half of item 54.
- **A utility bill paid by card** is saved as Utilities by the server, or Electric by the page, for gas and water too.
  Neither reaches the Gas estimate. Under item 54 the words would now say Gas, but the code is read first.
- **Child care is filed as tuition by the page**, and **insurance as Health Insurance**.

## 2. Points for ruling

**C1. One table, kept identical.** The page's code table is written from the server's: the same codes and the same
categories. A gate check compares them, as item 54 does for the words.
*Recommended.*

**C2. Leaves only.** Each code gets the leaf in the last column of the table. The named judgement calls:
- EV charging → Gas / Fuel, as fuel for the car;
- every school below college (8211) → School / Tuition, under Children / Family;
- the medical-equipment and nursing-care codes → Doctor / Co-pays.

*Recommended.*

**C3. No guess where the code covers more than one thing, or there is no leaf.** These codes name Other:
- 4900 and 4901 (every kind of utility);
- the insurance codes, which cover auto, home, life, health and pet;
- 4816 (internet providers and online services);
- 8999 (any professional service);
- 5921 (liquor; the tree has no leaf for it);
- 9311 (tax, as item 54 M5).

*Recommended.*

**C4. When the code names no leaf, the words decide.** Today a code always wins. Under C3 an AEP bill paid by card
with code 4900 would be Other, even though its words say Electric. So when a code's answer is Other, the words are
read instead, and only if they also name nothing does the row stay in Other. A code that names a leaf still wins.
*Recommended.*

**C5. What's already saved: item 54's review.** The review already asks today's rules about each row, code first.
Rows saved under an old code answer are offered from → to, with amounts, and moved only on a yes. The list of old
answers gains the page's code-era leaves that are now wrong for some codes: Personal Care for clothing, Health
Insurance, and Tuition / Courses for child care. A row whose new answer is Other is never offered.
*Recommended.*

**C6. Which line.** Master only, with item 54.
*Recommended: master only. This is your call under the 1.x rule.*

## 3. Not decided here

- **Codes missing from both tables.** A code neither table lists falls through to the words, which is the right
  default. Extending the table would be its own item.
- **A liquor or tax category** in the tree (C3, item 54 M5).
