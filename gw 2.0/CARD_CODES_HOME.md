# Item 85 - Home stores, general merchandise, and the bank's "Withdrawal"

Opened and built 2026-10-13/14. Found while building item 84. Rob: *"yes"* to fixing it the same way: the code
corrected, and his rows offered for moving with a yes.

## 1. What was wrong (measured on Rob's data)

- **Card codes for home stores named Rent / Mortgage.** These were 5200 home-supply (Lowe's, Menards), 5211 building
  materials, 5251 hardware, 5712 furniture, 5713 flooring and 5722 appliances.
  - Rob's Rent / Mortgage held no rent or mortgage payments at all: only Lowe's (17 rows, $787.45) and a carpet
    charge ($4.65).
  - Every one was counted as a housing payment, and protected as a necessity.
- **General-merchandise codes named Clothing.** These were 5310 discount, 5311 department, 5331 variety, 5399, 5999
  misc retail, 5969, 5932, 5732 electronics, 5942 (Amazon's historical code) and 5947 gift shops.
  - The importer's name rule for general retailers was labelled Clothing too: Amazon, Target, Dollar Tree, Best Buy,
    Harbor Freight, Wayfair, Tractor Supply. The tree had no leaf for general shopping.
- **Found while fixing that: the bare word "withdrawal" read as a transfer.**
  - Rob's bank starts every debit with *"Withdrawal …"*. Whenever a card code did not decide, a purchase was filed as
    a transfer, which counts as neither spending nor income.
  - In item 54's existing review this already offered AEP Ohio, Nationwide Pet Insurance and the county tax to
    Transfer.
  - Once the general-merchandise codes stopped deciding, Dollar Tree would have gone the same way.

## 2. The fix, under item 55's rules (C2 leaves only; C3 no guess where a code covers many things; C4 the words decide)

- **H1. The home codes:**
  - 5200, 5211, 5713 and 5722 → Home Improvement;
  - 5251 → Home Maintenance;
  - 5712 → Furniture / Decor.
- **H2. Codes that name no leaf:**
  - 5310, 5311, 5331, 5399, 5999, 5969, 5932 and 5732 cover many kinds of goods (C3), so the store's name decides;
  - 5942 too: Amazon uses it for everything, and mapping it to Books / Materials would have offered to move 56 of
    Rob's Amazon rows ($1,904) out of Shopping;
  - 5947 → Gifts.
- **H3. Shopping**, a leaf under Personal, for general retailers.
  - The one-time update creates it only where no *Shopping* exists. Rob's own is kept, with his Amazon and Walmart
    rules.
  - The name rule is split:
    - Shopping: Amazon, Target, Walmart, Dollar Tree, Dollar General, Family Dollar, Five Below, Temu, Best Buy,
      Costco.com, Wayfair, Tractor Supply, Harbor Freight;
    - Clothing: TJ Maxx, Kohl's, JCPenney, Macy's, Ross, Nordstrom, Marshalls, Indian Lake Outfitters.
- **H4. "Withdrawal" alone is not a transfer.** ATM and EFT withdrawals, and the named transfer phrases, still are.
- **H5. The review offers what the corrected rules file differently,** moved only on a yes, and never to Other.
  - It now also looks at Rent / Mortgage and Clothing, and at rows carrying a corrected code.
  - On a copy of Rob's data:
    - Lowe's and the carpet, 18 rows ($792.11) → Home Improvement;
    - Dollar Tree, Dollar General and Five Below, 44 rows ($1,145.87) → Shopping;
    - the hospital gift shop, 3 rows → Gifts.
  - Item 84's EV rows are offered too. After H4 the review offers nothing to Transfer.
- **Not offered here:** purchases already filed as Transfer (some Lowe's, Petco and Walgreens rows). Some may be
  store-card payments, so item 83's per-merchant question is where they are answered.

## 3. Built

- `bank_importer.py`: the codes, the split name rule, the transfer rule. The page's copies are kept identical (s166,
  s167).
- `core/database.py` CATEGORY_TREE: Shopping. `migrate.py`: SCHEMA `20261014-home-codes`, fixture written.
- `server._regroup_review`: H5.
- **Tests:** s225, 6 checks. s166 and s167 pass with the page matching the importer.

## 4. Status

Built 2026-10-14. Awaiting Rob's acceptance and push word.
