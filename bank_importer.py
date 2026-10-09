"""
bank_importer.py — Multi-format import (CSV / QFX / OFX / QIF / TXT) for Groundwork.

Detects file format from contents (OFX SGML header, QIF !Type marker,
or CSV row shape) and normalizes every row into Groundwork's transaction
record format:

    {
        'date':         'YYYY-MM-DD',
        'description':  str,
        'amount':       float (always positive),
        'type':         'debit' | 'credit',
        'category':     str (one of GROUNDWORK_CATEGORIES),
        'raw_category': str,   # original bank category, '' if none
        'cleared':      bool,
    }

Mirrors `clientAutoCategory()` in app.js so server- and client-side
fallback categorization stay in sync.
"""

import csv
import io
import re
from datetime import datetime


GROUNDWORK_CATEGORIES = [
    # Core
    'Food', 'Groceries', 'Coffee Shops', 'Restaurants', 'Fast Food / Takeout',
    'Transportation', 'Gas / Fuel', 'Car Maintenance',
    'Rent / Mortgage', 'Home Maintenance',
    'Utilities', 'Phone / Cell',
    'Clothing', 'Personal',
    'Entertainment', 'Streaming Video', 'Subscriptions', 'Hobbies',
    'Healthcare', 'Pet Food / Supplies',
    'Insurance',
    'Income', 'Income',
    'Debt', 'Transfer',
    'Charitable Donations', 'Haircut / Salon', 'Vacation / Travel', 'Education',
    'Transfer', 'Interest / Fees', 'Property Taxes',
    'Other',
]


# ── MCC-based categorization ────────────────────────────────────────────────
# A 4-digit merchant category code from a card-swipe is a definitive signal,
# far more reliable than keyword matching against unfamiliar merchant names.
# This table was rebuilt against a real-world 952-transaction QFX export,
# which had 45 distinct MCCs across real usage. Mappings are calibrated
# to what merchants actually fall under each code in his data, not generic
# theory. For codes not in real data, we extend with reasonable defaults
# from the ISO 18245 standard.
MCC_CATEGORY_MAP = {
    # ── Food (sit-down, fast-food, bars, bakeries) ──
    '5812': 'Restaurants',     # Eating places (Beer Barrel, Kewpee, Buffalo Wild Wings)
    '5813': 'Restaurants',     # Drinking places / bars
    '5814': 'Fast Food / Takeout',       # Fast food (Tropical Smoothie, Starbucks, Wingstop)
    '5499': 'Groceries',      # Misc food stores (West Baden in his data)

    # ── Groceries ──
    '5411': 'Groceries',      # Grocery stores (Chief Supermarket, Meijer, Aldi)
    '5422': 'Groceries',      # Meat markets
    '5441': 'Groceries',      # Candy/nut/confectionery
    '5451': 'Groceries',      # Dairy products
    '5462': 'Groceries',      # Bakeries

    # ── Transportation: split between Gas / Fuel, Car Maintenance, Transportation
    # (item 52: 'Gas / Fuel' is the Transportation leaf; bare 'Gas' is the natural-gas utility)
    '5541': 'Gas / Fuel',     # Service stations w/ pumps (Clark Gas, BP, Marathon)
    '5542': 'Gas / Fuel',     # Automated fuel dispensers
    '5552': 'Transportation', # Electric vehicle charging (NAYAX EV in his data)
    '5172': 'Gas / Fuel',     # Petroleum and petroleum products
    '7542': 'Car Maintenance',    # Car washes (Whitewater Car Wash)
    '7538': 'Car Maintenance',    # Auto service shops
    '5511': 'Car Maintenance',    # Car/truck dealers
    '5531': 'Car Maintenance',    # Auto/home supply stores
    '5532': 'Car Maintenance',    # Automotive tire stores
    '5533': 'Car Maintenance',    # Automotive parts
    '4111': 'Transportation', # Commuter transport
    '4121': 'Transportation', # Taxicabs / rideshare
    '4131': 'Transportation', # Bus lines
    '4789': 'Transportation', # Transportation services - misc
    '7523': 'Transportation', # Parking lots

    # ── Housing & home services ──
    '5200': 'Rent / Mortgage',        # Home supply warehouses (Lowe's, Menards)
    '5211': 'Rent / Mortgage',        # Lumber/building materials
    '5231': 'Home Maintenance',   # Glass/paint/wallpaper (Sherwin-Williams)
    '5251': 'Rent / Mortgage',        # Hardware stores
    '5712': 'Rent / Mortgage',        # Furniture/home furnishings
    '5713': 'Rent / Mortgage',        # Floor covering / carpets (Masland Carpets)
    '5722': 'Rent / Mortgage',        # Household appliances
    '1520': 'Home Maintenance',   # General contractors
    '1711': 'Home Maintenance',   # Plumbing/heating/AC

    # ── Utilities, telecom, streaming
    '4814': 'Phone / Cell',          # Telecom services (cell, long distance)
    '4815': 'Phone / Cell',
    '4812': 'Phone / Cell',          # Telecom equipment
    '4816': 'Subscriptions',   # Computer network/info services
    '4899': 'Streaming Video',      # Cable/satellite/streaming (Spectrum, Disney+, Netflix)
    '4900': 'Utilities',      # Electric/gas/water/sanitary (City of Millbrook)
    '4901': 'Utilities',

    # ── Healthcare & pets
    '0742': 'Pet Food / Supplies',            # Veterinary services (Heidt Vet, Metz Petz)
    '0743': 'Pet Food / Supplies',
    '5995': 'Pet Food / Supplies',            # Pet shops/food/supplies (Petco, Chewy)
    '5912': 'Healthcare',     # Drug stores / pharmacies (Walgreens)
    '5122': 'Healthcare',     # Drug proprietary
    '8011': 'Healthcare',     # Doctors / physicians
    '8021': 'Healthcare',
    '8031': 'Healthcare',
    '8041': 'Healthcare',
    '8042': 'Healthcare',
    '8043': 'Charitable Donations',        # Opticians/eyewear — but real data has Goodwill here so leaning Charity
    '8050': 'Healthcare',
    '8062': 'Healthcare',     # Hospitals
    '8071': 'Healthcare',     # Medical labs
    '8099': 'Healthcare',
    '5047': 'Healthcare',     # Medical equipment

    # ── Insurance
    '5960': 'Insurance',      # Direct marketing insurance (Nationwide Pet Insurance)
    '6300': 'Insurance',      # Insurance sales/underwriting
    '6381': 'Insurance',

    # ── Shopping (specific stores)
    '5311': 'Clothing',       # Department stores (JCPenney)
    '5310': 'Clothing',       # Discount stores (TJ Maxx)
    '5300': 'Groceries',      # Wholesale clubs (Sam's Club — primarily groceries here)
    '5331': 'Clothing',       # Variety stores (Dollar Tree, Dollar General)
    '5399': 'Clothing',       # Misc general merch
    '5621': 'Personal',       # Women's ready-to-wear (Francesca's)
    '5651': 'Personal',       # Family clothing
    '5661': 'Personal',       # Shoe stores
    '5691': 'Personal',
    '5732': 'Clothing',       # Electronics
    '5734': 'Subscriptions',   # Computer software stores (Anthropic — software subscription)
    '5942': 'Clothing',       # Book stores (Amazon historical MCC)
    '5970': 'Hobbies',          # Artist supplies (Cricut, Michaels)
    '5945': 'Hobbies',          # Hobby/toy/game shops (Hobby Lobby, Build-A-Bear)
    '5947': 'Clothing',       # Gift shops
    '5968': 'Subscriptions',   # Direct marketing — subscription merchants
    '5969': 'Clothing',
    '5818': 'Subscriptions',   # Digital goods (Apple subscriptions)
    '5732': 'Clothing',
    '5999': 'Clothing',       # Misc specialty retail (Harbor Freight)
    '5932': 'Clothing',       # Antique shops (Indian Lake Outfitters in his data)
    '5921': 'Personal',       # Package stores - liquor

    # ── Personal services
    '7230': 'Haircut / Salon',         # Barber/beauty shops (What a Tease)
    '7297': 'Haircut / Salon',         # Massage parlors
    '7298': 'Haircut / Salon',         # Health/beauty spas
    '7261': 'Other',          # Funeral services
    '7311': 'Other',
    '7372': 'Subscriptions',   # Computer services
    '5977': 'Haircut / Salon',         # Cosmetic stores

    # ── Recreation
    '7832': 'Entertainment',  # Movie theaters
    '7841': 'Streaming Video',      # Video tape rental
    '7922': 'Entertainment',  # Theatrical producers
    '7929': 'Entertainment',
    '7991': 'Entertainment',
    '7993': 'Entertainment',
    '7994': 'Entertainment',  # Video game arcades
    '7996': 'Entertainment',  # Amusement parks
    '7997': 'Gym / Fitness',  # Country clubs / fitness clubs
    '7999': 'Vacation / Travel',         # Recreation services - travel

    # ── Charity / public
    '8398': 'Charitable Donations',        # Charitable orgs (GoFundMe)
    '8661': 'Charitable Donations',        # Religious orgs
    '8398': 'Charitable Donations',
    '9211': 'Interest / Fees',           # Court costs
    '9222': 'Interest / Fees',           # Fines
    '9223': 'Interest / Fees',
    '9311': 'Property Taxes',          # Tax payments
    '9399': 'Interest / Fees',           # Govt services (BMV in his data — DMV fees)

    # ── Education
    '8211': 'Education',      # Elementary/secondary schools
    '8220': 'Education',      # Colleges/universities
    '8241': 'Education',
    '8244': 'Education',
    '8249': 'Education',
    '8299': 'Education',
    '8351': 'Education',      # Child care services

    # ── Childcare
    '8351': 'Education',      # Child care services (re-asserting — same MCC as 8351 above)

    # ── Financial
    '6010': 'Transfer',       # Manual cash disbursement
    '6011': 'Transfer',       # ATM cash advance
    '6012': 'Debt',           # Financial institutions — merchant svcs (Synchrony, credit-card payments)
    '6051': 'Transfer',       # Quasi-cash
    '6211': 'Transfer',        # Securities/brokers
    '4829': 'Transfer',       # Wire transfer / money orders (Apple Cash, Cash App, Venmo)
    '6536': 'Transfer',       # Money transfer

    # ── Misc
    '8931': 'Interest / Fees',           # Accounting/tax (TaxSlayer)
    '8999': 'Subscriptions',   # Professional services - Experian credit
    '8911': 'Other',          # Architectural/engineering
}


# ── Auto-categorization keyword patterns ───────────────────────────────────
# Used when no MCC is present (mostly ACH transfers, check transactions,
# and Quicken-style descriptions without card-network metadata). Patterns
# are scanned in list order — FIRST MATCH WINS — so SPECIFIC patterns must
# come BEFORE GENERIC ones. Streaming before Subscription, Pet before
# Healthcare, Groceries before Food, etc.
#
# Rebuilt against the canonical merchant dictionary in _MERCHANT_MAP
# so every merchant we already know about lands in the right category.
# Keep in sync with clientAutoCategory() in app.js.

_CATEGORY_PATTERNS = [
    # Item 54 (MATCHER_ONE_ANSWER.md, Rob 2026-10-09): this table is THE rule set. clientAutoCategory() in app.js
    # carries the same rules - same words, same leaf, same order - and s166 fails if they differ (M1). Every rule
    # names a leaf, never a parent (M2); words that name more than one service name 'Other', so the row waits for
    # the user rather than a guess the estimates would trust.

    # ── INTEREST CHARGES - before Debt, so a card's interest and its payment stay apart (M3: from the page's copy)
    ('Interest / Fees', r'\binterest charge\b|\binterest charged\b|\bfinance charge\b|\bperiodic rate\b|'
                        r'\bpurchase interest\b|\bcash advance interest\b|\bbalance transfer interest\b|'
                        r'\bint chg\b|\bfinance chg\b'),

    # ── DEBT first (biggest single fix from baseline analysis)
    # Credit cards, auto loans, student loans, financial holding companies.
    # These come in as ACH/check rows with no MCC, so keyword is the only signal.
    ('Debt', r'\bcapital one\b|\bapple\s*card\b|\bchase credit\b|\bbarclay|'
             r'\bcomenity\b|\bonemain\b|\bsynchrony\b|\bsyncb\b|'
             r'\bford motor (cr|credit)\b|\bstellantis\b|\bdept(\.|\s)+education\b|'
             r'\bdoe payment\b|\bsallie mae\b|\bnavient\b|\bnelnet\b|'
             r'\bdiscover\b.*(payment|card)|'
             r'\bcredit card payment\b|\bcard payment.*thank you\b|'
             r'\bthank you.*payment\b|\bminimum payment\b|\bcc payment\b'),

    # ── INCOME (specific employers + standard payroll markers)
    # Must come BEFORE the Transfer block below: Transfer's generic
    # \bdeposit\b would otherwise match every real paycheck description
    # first (nearly all contain the word "deposit"), making these more
    # specific payroll patterns unreachable and silently miscategorizing
    # every direct-deposit paycheck as Transfer instead of Income.
    ('Paycheck / Salary', r'\bpayroll\b|'
               r'\bdirect dep(osit)?\b|\bsalary\b|\bach credit.*deposit\b'),
    # M5: the tree has no tax leaf - a tax refund waits in Other for the user
    ('Other', r'\birs\s*treas\s*310\b|\btax refund\b'),

    # ── TRANSFER (own accounts, peer-to-peer, ATM, checks, bank-to-bank)
    # Moved up: needs to come before generic fallbacks since these are
    # signals of money MOVING, not category-meaningful spending.
    ('Transfer', r'\btransfer (to|from)\b|\bach transfer\b|'
                 r'\binternal transfer\b|\bonline transfer\b|'
                 r'\bvenmo\b|\bcash app\b|\bzelle\b|\bpaypal\s+(transfer|p2p)\b|'
                 r'\bwithdrawal\b|\batm\s+(eft|withdraw)\b|\bat atm\b|\beft withdrawal\b|'
                 r'\bdraft\s+\d|\bcheck received\b|\bdeposit\b|'
                 r''
                 r'\btransactor:\b'),

    # ── REFUND (often paired with merchant name — match when reversal/refund/credit memo). M4: Transfer, so it
    # counts in neither income nor spending; it does not reduce the original category's spending (named limit).
    ('Transfer', r'\brefund\b|\breversal\b|\bchargeback\b|\bcredit memo\b|'
               r'\breturn.{0,10}(credit|merch)|\bmerchandise return\b'),

    # ── TRANSFER (between own accounts)
    ('Transfer', r'\btransfer (to|from)\b|\bach transfer\b|'
                 r'\binternal transfer\b|\bonline transfer\b'),

    # ── SAVINGS (specific brokerage/retirement)
    ('Transfer', r'\btransfer.{0,10}sav\b|\bsavings (account|deposit)\b|'
                r'\bfidelity\b|\bvanguard\b|\bschwab\b|\b401\s*k\b|'
                r'\broth ira\b|\bbrokerage\b'),

    # ── STREAMING (must come before Subscription — Netflix could match either)
    ('Streaming Video', r'\bnetflix\b|\bhulu\b|\bdisney(plus|\+)?\b|\bspotify\b|'
                  r'\bapple music\b|\bhbo (max)?\b|\bparamount\b|'
                  r'\bpeacock\b|\byoutube (premium|tv)\b|\bsling tv\b|\bstarz\b'),

    # ── SUBSCRIPTION (software, news, services with recurring fee)
    ('Software / Apps', r'\banthropic\b|\bopenai\b|\bclaude\.ai\b|\bchatgpt\b|'
                     r'\bapple\.com\/bill\b|\bgoogle storage\b|\bicloud\b|'
                     r'\bdropbox\b|\bmicrosoft\b.*(365|subscription)|'
                     r'\badobe\b|\brocket money\b|\bexperian\b|\bcredit karma\b'),
    ('Other Subscriptions', r'\bnyt(imes)?\b|\bwashington post\b|\bsubscription\b'),

    # ── PHONE (split out from Utilities)
    ('Phone / Cell', r'\bat\s*&?\s*t\b|\battinternet\b|\battpayment\b|'
              r'\bverizon\b|\bt-?mobile\b|\bsprint\b|\bmint mobile\b|'
              r'\bus cellular\b|\bcricket wireless\b|\bvisible\b'),

    # ── UTILITIES (electric, gas, water, trash — NOT phone, NOT cable)
    ('Gas', r'\benbridge\b|\bdominion (energy )?gas\b|\bcolumbia gas\b|\bgas (company|utility)\b'),
    ('Electric', r'\baep\b|\bohio edison\b|\bdominion power\b|\bsce\b|\bsouthern california edison\b|'
                 r'\belectric (bill|company)\b'),
    ('Water / Sewer', r'\bwater (dept|utility|bill)\b|\bsewer\b|\bsewage\b'),
    ('Trash', r'\btrash (service|pickup)\b'),
    # Gas AND electric from one company, or a bill that doesn't say which: no guess
    ('Other', r'\bduke energy\b|\bdominion energy\b|\bnational grid\b|\bpge\b|\butility (bill|payment)\b'),

    # ── INSURANCE (must come before Pet, Nationwide Pet Insurance is in Pet)
    # Order: most specific first
    ('Pet Food / Supplies', r'\bnationwide\s+pet\b|\bpetco\b|\bchewy\b|'
            r'\bbanfield\b|\bvet (clinic|hospital|services)\b|\bveterinary\b|'
            r'\bpetsmart\b|\bpet supplies\b|\bflying fur pets\b'),

    # Carriers: Auto Insurance, the most common recurring charge from them - a user re-files home or life
    ('Auto Insurance', r'\bgeico\b|\bprogressive\b|\bstate farm\b|\ballstate\b|'
                  r'\bnationwide\b|\bliberty mutual\b|\busaa\b|\bfarmers\b'),
    ('Other', r'\binsurance\b'),

    # ── GAS / FUEL (must come before Transportation). Item 52: 'Gas / Fuel' is the
    # Transportation leaf; bare 'Gas' is the natural-gas UTILITY leaf, where fuel used to land.
    # Item 53 (FUEL_NAMES.md): the station names. G6 - this is the same text as the fuel test in
    # clientAutoCategory() in app.js; s165 fails if they differ. A name that is also a word or another
    # business (Pilot, Holiday, Gulf, Marathon ...) counts only with a store number or a station word.
    ('Gas / Fuel', (
        r"\bclark (gas|oil|station)?\b|"
        r"\bbp(\s|#|\d)|"
        r"\bexxon|"
        r"\bmobil\b|"
        r"\bshell\b|"
        r"\bspeedway\b|"
        r"\bcircle k\b|"
        r"\bsunoco\b|"
        r"\bchevron\b|"
        r"\b76\s+(gas|fuel)\b|"
        r"\bbuc.ee|"
        r"\bsheetz\b|"
        r"\bwawa\b|"
        r"\bphillips 66\b|"
        r"\bconoco\b|"
        r"\bcitgo\b|"
        r"\bvalero\b|"
        r"\bquik ?trip\b|"
        r"\bracetrac\b|"
        r"\bkwik trip\b|"
        r"\bmurphy (usa|express)\b|"
        r"\bthorntons\b|"
        r"\bta travel\b|"
        r"\bget ?go\b|"
        r"\bspeedy q\b|"
        r"\bcumberland farms\b|"
        r"\bflying j\b|"
        r"\bmarathon(\s+petro|\s*#|\s+\d)|"
        r"\bpilot(\s*#|\s+\d|\s+travel)|"
        r"\blove\x27?s(\s*#|\s+\d|\s+travel|\s+country)|"
        r"\bholiday(\s+stations?|\s+oil|\s*#|\s+\d)|"
        r"\bgulf(\s+oil|\s*#|\s+\d)|"
        r"\barco(\s*#|\s+\d)|"
        r"\bqt(\s*#|\s+\d)|"
        r"\bcasey\x27?s(\s+gen|\s*#|\s+\d)|"
        r"\bsinclair(\s+oil|\s*#|\s+\d)|"
        r"\b(costco|sam\x27?s(\s+club)?)\s+(gas|fuel)\b|"
        r"\bmeijer express\b|"
        r"\bfuel|"
        r"\bgas station\b"
    )),

    # ── AUTO SERVICE
    ('Car Maintenance', r'\bjiffy lube\b|'
                    r'\bvalvoline\b|\bmidas\b|\bfirestone\b|\bpep boys\b|'
                    r'\bmechanic\b|\bauto (service|repair|parts)\b|\boil change\b|'
                    r'\bcar wash\b|\btire (shop|store|center)\b'),

    # ── TRANSPORTATION (rideshare, parking, transit — NOT gas)
    ('Rideshare / Transit', r'\buber\b(?!\s+eats)|\blyft\b|'
                       r'\bmetro (transit|card)\b|\bbus pass\b|'
                       r'\bbart\b|\bmta\b|\bamtrak\b|\bgreyhound\b'),
    ('Parking / Tolls', r'\bparking\b|\btoll\b'),

    # ── HOUSING
    ('Rent / Mortgage', r'\bmortgage\b|\brent (payment|check)\b|\blandlord\b|\bhoa fees?\b|'
                r'\bproperty tax\b|\bhome depot\b|\blowe.?s\b|\bmenards|\bmnrd\b'),

    # ── HOME SERVICES
    ('Home Maintenance', r'\bsherwin.?williams\b|\bbenjamin moore\b|'
                     r'\broto.rooter\b|\bplumb(er|ing)\b|\bhvac\b|\belectrician\b|'
                     r'\blawn (care|service|mow)\b|\bpest control\b|\borkin\b|'
                     r'\bterminix\b|\bcontractor\b|\bcleaning service\b'),

    # ── GROCERIES (specific big-box groceries — must come before Food)
    ('Groceries', r'\bwalmart\b|\bwal-?mart\b|\bwm supercenter\b|\bkroger\b|'
                  r'\bmeijer\b|\bsam.?s\s*club\b|\bsamsclub\b|\bcostco\b|\baldi\b|'
                  r'\bruler foods\b|\bwhole foods\b|'
                  r'\bsprouts\b|\btrader joe.?s\b|\bsafeway\b|\bpublix\b|'
                  r'\bgrocery\b'),

    # ── COFFEE (specific — must come before Food/Restaurant)
    ('Coffee Shops', r'\bstarbucks\b|\btropical smoothie\b|\bdunkin\b|\btim hortons\b|'
               r'\bpeet.?s coffee\b|\bblue bottle\b|\bcaribou (coffee)?\b|'
               r'\bcoffee (shop|house|company)\b'),

    # ── FAST FOOD (specific — must come before Food/Restaurant)
    # Note: trailing \b is OMITTED for many brand names because real bank
    # descriptions append "S" (WENDYS, JIMMY JOHNS, etc.) which a strict
    # \b...\b would not match.
    ('Fast Food / Takeout', r'\bbuffalo wild|\bbwr\b|\bwingstop|'
                 r'\braising canes?|\b5\s*guys|\bfive guys|'
                 r'\bdomino|\bpapa john|\bchipotle|\btaco bell|'
                 r'\bmcdonald|\bburger king|\bwendy|\bsubway\b|'
                 r'\bdairy queen|\bsonic\b|\bchick.?fil.?a|\bpopeye|'
                 r'\bkfc\b|\bjimmy john|\bpanera bread|\bquizno|'
                 r'\bdoordash|\bgrubhub|\bubereats|\buber eats'),

    # ── RESTAURANT (sit-down — must come before generic Food)
    ('Restaurants', r'\btexas roadhouse\b|\bolive garden\b|\bapplebee|'
                   r'\bred lobster\b|\bcheesecake (factory)?\b|'
                   r'\bbob evans\b|'
                   r''
                   r''
                   r'\bibuy\b|\bdenny.?s\b|\bcracker barrel\b'),

    # ── FOOD (generic fallback — caught by MCC 5814/5812 in most card-swipes
    # so this only catches ACH/check rows referencing food)
    ('Restaurants', r'\bfood\b|\brestaurant\b|\bdiner\b|\bcafe\b|\bbar\s|\bgrill\b'),

    # ── HEALTHCARE (broad — pharmacies, docs, hospitals)
    ('Dental', r'\bdental\b|\bdentist\b|\bortho'),
    ('Vision', r'\bvision center\b'),
    # Pharmacy chains: Prescriptions (named judgement - they also sell everyday goods)
    ('Prescriptions', r'\bwalgreens\b|\bcvs\b|\brite\s*aid\b|\bduane reade\b|\bpharmacy\b'),
    ('Doctor / Co-pays', r'\bdoctor\b|\bdr\.|\bhospital\b|\bclinic\b|'
                   r'\bmedical (center|group|services)\b|\bhealthcare\b|'
                   r'\bresource recycl\b'),

    # ── HOBBY
    ('Hobbies', r'\bhobby lobby\b|\bcricut\b|\bmichaels\b|\bjoann\b|'
              r'\bbuild.a.bear\b|\bgame stop\b|\bbarnes.{0,3}noble\b|'
              r'\bguitar center\b|\bcraft (store|supplies)\b'),

    # ── BEAUTY
    ('Haircut / Salon', r'\bsephora\b|\bulta\b|\bsally beauty\b|'
               r'\bsalon\b|\bbarber\b|\bspa\b|\bnail (salon|shop)\b|\bhair (cut|salon)\b'),

    # ── TRAVEL
    ('Vacation / Travel', r'\bairlines?\b|\bdelta air\b|\bunited air\b|\bsouthwest air\b|'
               r'\bamerican airlines\b|\bspirit airlines\b|\bjetblue\b|'
               r'\bhotel\b|\bmotel\b|\bmarriott\b|\bhilton\b|\bairbnb\b|\bvrbo\b|'
               r'\bexpedia\b|\bbooking\.com\b|\bkayak\b|\btravelocity\b|'
               r'\benterprise rent\b|\bhertz\b|\bbudget rent\b'),

    # ── CHARITY (after specific brands resolved)
    ('Charitable Donations', r'\bgoodwill\b|\bgofundme\b|\bsalvation army\b|\bred cross\b|'
                r'\bunited way\b|\bdonation\b|\bcharity\b|\bnonprofit\b'),

    # ── ENTERTAINMENT (events, theaters, recreation — non-streaming)
    ('Activities / Events', r'\bcinemark\b|\bregal (cinemas)?\b|\bamc theatre|'
                      r'\bmovie theater\b|\bconcert\b|\bticketmaster\b|'
                      r'\bstubhub\b|\bvenue\b|\bveterans memorial\b'),

    # ── FITNESS ('Gym / Fitness' is the Healthcare leaf; 'Fitness' is not in the tree - item 52)
    ('Gym / Fitness', r'\bplanet fitness\b|\banytime fitness\b|\bla fitness\b|'
                r'\bequinox\b|\bgym\b|\bcrossfit\b|\bpeloton\b|'
                r'\byoga (studio|class)\b'),

    # ── EDUCATION (not student loans — see Debt)
    ('Tuition / Courses', r'\btuition\b|\buniversity (of|payment)\b|\bcollege payment\b|'
                  r'\bschool (district|fees|payment)\b|\btextbook\b'),

    # ── FEES (bank fees, late fees, ATM fees)
    ('Interest / Fees', r'\bservice (fee|charge)\b|\bnsf fee\b|\boverdraft\b|'
             r'\batm fee\b|\bforeign transaction fee\b|\blate (fee|charge)\b|'
             r'\bmaintenance fee\b|\battempt fee\b|\bohio bmv\b|\bdmv\b|'
             r'\btaxslayer\b'),

    # ── TAXES (M5: the tree has no income-tax leaf, and Property Taxes / Interest / Fees were both wrong) - no guess
    ('Other', r'\birs (payment|tax)\b|\bstate tax\b|\bfederal tax\b|'
              r'\btreasury\b'),

    # ── SHOPPING (catches Amazon, dept stores, TJ Maxx, etc.)
    # Trailing \b omitted on brand names that often appear smushed
    # (DOLLARTREE, TJMAXX, JCPENNEY) without word boundaries.
    ('Clothing', r'\bamazon|\bamzn\b|\btj\s*maxx|\btjx\b|\bjcpenney|'
                 r'\bkohl.?s|\btarget\b|\bmacy.?s|\bdollar\s*tree|\bdollartree|'
                 r'\bdollar.general|\bross\b|\bnordstrom|\bmarshall.?s|'
                 r'\bbest buy\b|\bcostco\.com|\bwayfair|'
                 r'\bindian lake outfitters|\bfamily dollar|\bfamilydollar|'
                 r'\btractor.?supply|\bharbor freight'),

    # ── PERSONAL (specific small-business / boutique clothing & services)
    ('Personal Care', r'\bfrancesca\b|\bdry clean(er)?\b|\blaundromat\b|'
                 r'\btailor\b|\bcobbler\b'),
]


def auto_category(description: str, mcc: str = '') -> str:
    """Categorize a transaction — MCC (definitive) takes priority over keyword matching."""
    if mcc and mcc in MCC_CATEGORY_MAP:
        return MCC_CATEGORY_MAP[mcc]
    d = (description or '').lower()
    for category, pattern in _CATEGORY_PATTERNS:
        if re.search(pattern, d):
            return category
    return 'Other'


# ── Date parsing ─────────────────────────────────────────────────────────────

_DATE_FORMATS = ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y')


def _parse_date(s: str):
    """Parse common bank date formats. Returns ISO string or None."""
    if not s:
        return None
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_amount(s: str):
    """Parse a currency string like '$1,234.56' or '(45.00)' into a float."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    negative = s.startswith('(') and s.endswith(')')
    s = s.strip('()').replace('$', '').replace(',', '').strip()
    if not s:
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if negative else val


# ── Rich description parser ─────────────────────────────────────────────────
# Ledger Redesign Blueprint §3/§10. Superior CU (and similarly-shaped card
# processors) embed structured data inside the free-text description:
#   "...CHECK CARD TRAN KEWPEE HAMBURGERS W 419-2352754 OH Date 06/17/26 010407 5812 Card 6942"
# breaks down as: merchant name, [phone/ref], the TRUE transaction date
# (vs. the column's POSTING date), an internal reference number, the MCC,
# and the card's last 4 digits. The original description is preserved
# verbatim by the caller (stored in `memo`), so nothing is lost by parsing.

_RICH_TAIL_RE = re.compile(
    r'Date\s+(\d{2}/\d{2}/\d{2})\s+\d+\s+(\d{4})\s+Card\s+(\d{4})\s*$'
)
_CARD_ONLY_RE = re.compile(r'Card\s+(\d{4})\s*$')

_LEADING_PREFIXES = [
    re.compile(r'^Recurring Withdrawal CHECK CARD TRAN\s+', re.IGNORECASE),
    re.compile(r'^Withdrawal CHECK CARD TRAN\s+', re.IGNORECASE),
    re.compile(r'^Withdrawal Adjustment Credit Voucher\s+', re.IGNORECASE),
    re.compile(r'^Withdrawal POS #\d+\s+', re.IGNORECASE),
    re.compile(r'^Withdrawal at ATM #\d+\s+', re.IGNORECASE),
    re.compile(r'^Recurring Withdrawal ACH\s+', re.IGNORECASE),
    re.compile(r'^Withdrawal ACH\s+', re.IGNORECASE),
    re.compile(r'^Deposit ACH\s+', re.IGNORECASE),
    re.compile(r'^Recurring Withdrawal\s+', re.IGNORECASE),
    re.compile(r'^Withdrawal\s+', re.IGNORECASE),
    re.compile(r'^Deposit\s+', re.IGNORECASE),
]
_ACH_TAIL_RE = re.compile(r'\s+TYPE:.*$', re.IGNORECASE)


def parse_rich_description(raw_desc: str) -> dict:
    """
    Extract true_date / mcc / card_last4 / merchant from a card-network-style
    description string. Fields absent from a given row (e.g. ACH transactions
    have no card/MCC/embedded date) stay None.
    """
    desc = (raw_desc or '').strip()
    true_date = mcc = card_last4 = None
    working = desc

    m = _RICH_TAIL_RE.search(working)
    if m:
        mm, dd, yy = m.group(1).split('/')
        true_date = f'20{yy}-{mm}-{dd}'
        mcc = m.group(2)
        card_last4 = m.group(3)
        working = working[:m.start()].rstrip()
    else:
        m2 = _CARD_ONLY_RE.search(working)
        if m2:
            card_last4 = m2.group(1)
            working = working[:m2.start()].rstrip()

    working = _ACH_TAIL_RE.sub('', working).rstrip()

    for prefix_re in _LEADING_PREFIXES:
        stripped = prefix_re.sub('', working)
        if stripped != working:
            working = stripped.strip()
            break

    merchant = working.strip() or desc  # never return an empty merchant

    # CP5 — final canonicalization pass: strip generic noise (state codes,
    # phone numbers, store numbers, street addresses, POS prefixes) and
    # map to canonical brand names. Two-stage by design so the dictionary
    # only deals with already-noise-free strings, and the noise stripper
    # produces something readable even for merchants not in the dictionary.
    merchant = _canonicalize_merchant(merchant)

    return {
        'true_date':  true_date,
        'mcc':        mcc,
        'card_last4': card_last4,
        'merchant':   merchant,
    }


# ── CP5: merchant canonicalization ─────────────────────────────────────────
# Designed against a real-world 973-row credit-union CSV. Reduced 268 distinct
# raw merchant strings to 170 canonical ones.
#
# Stage 1 (NOISE_PATTERNS): generic regex strippers that work on any bank's
# data, not Superior-specific. Run iteratively so a state code revealed
# after a city strip also gets removed.
#
# Stage 2 (MERCHANT_MAP): brand dictionary — `pattern → canonical name`.
# Patterns use word boundaries so partial matches stay safe ("Bear" in
# "Build-A-Bear" doesn't match "Beer Barrel"). Order is loosely most-
# specific first: SYNCB matches before generic synchrony, Apple Card
# before Apple, Nationwide Pet before Nationwide.
import re as _re

_NOISE_PATTERNS = [
    # 2-letter state suffix at end (preceded by space): " OH", " CA", " WA"
    (_re.compile(r'\s+[A-Z]{2}\s*$'), ''),
    # Phone number anywhere: 419-2352754, 800-782-7282, 408-5403700
    (_re.compile(r'\s*\d{3}[-\s]\d{3,}[-\s]?\d{0,4}\s*'), ' '),
    # Street address: "1234 ABC RD/ST/BLVD MILLBROOK"
    (_re.compile(r'\s+\d{1,5}\s+[A-Z][A-Z\s]+(?:RD|ROAD|ST|STREET|BLVD|DR|DRIVE|AVE|AVENUE|WAY|LANE|LN|CHAPEL|HWY)(?:\s+[A-Z]+)?(?:\s+\d+)?', _re.I), ''),
    # Store number patterns: #1330, #00255*, " 659", "STORE 659"
    (_re.compile(r'\s*#?\s*0*\d{3,6}\s*\*?'), ' '),
    # Web suffixes at end: " amazon.com", " /bill", etc
    (_re.compile(r'\s+(?:[\w.]+\.(?:com|net|org)(?:[/\w-]+)?)\s*$', _re.I), ''),
    # POS noise prefixes — TST*, SQ *, VC*, IN *, CKE*, DD * (DoorDash)
    # Note: SYNCB is intentionally NOT here (it identifies the brand, see dict)
    (_re.compile(r'^(?:TST\*|SQ\s*\*|VC\*|IN\s*\*|CKE\*|DD\s*\*|POS\s*\d+)\s*', _re.I), ''),
    # Trailing single-letter store branch codes (KEWPEE HAMBURGERS W)
    (_re.compile(r'\s+[A-Z]\s*$'), ''),
]

def _strip_noise(s):
    """Iteratively apply noise patterns until the string stabilizes."""
    out = s
    for _ in range(3):
        before = out
        for pat, repl in _NOISE_PATTERNS:
            out = pat.sub(repl, out)
        out = _re.sub(r'\s+', ' ', out).strip()
        if out == before:
            break
    return out

# Brand dictionary. Each entry: (compiled pattern, canonical name).
# Order matters — more-specific patterns must come first.
_MERCHANT_MAP = [
    # Groceries / big-box
    (r'\bwal-?mart\b|\bwm supercenter\b',     'Walmart'),
    (r'\bkroger\b',                            'Kroger'),
    (r'\bmeijer\b',                            'Meijer'),
    (r'\bsam\'?s\s*club\b',                    "Sam's Club"),
    (r'\btarget\b',                            'Target'),
    (r'\baldi\b',                              'Aldi'),
    (r'\bcostco\b',                            'Costco'),
    (r'\bdollar tree\b',                       'Dollar Tree'),
    (r'\bdollar.general\b',                    'Dollar General'),
    (r'\bruler foods\b',                       'Ruler Foods'),
    # Food / restaurants
    (r'\bstarbucks\b',                         'Starbucks'),
    (r'\btropical smoothie\b',                 'Tropical Smoothie'),
    (r'\bbuffalo wild\b|\bbwr\b',              'Buffalo Wild Wings'),
    (r'\btexas roadhouse\b',                   'Texas Roadhouse'),
    (r'\bapplebee',                            "Applebee's"),
    (r'\bolive garden\b',                      'Olive Garden'),
    (r'\bchipotle\b',                          'Chipotle'),
    (r'\bdomino',                              "Domino's"),
    (r'\braising canes?\b',                    "Raising Cane's"),
    (r'\bwingstop\b',                          'Wingstop'),
    (r'\b5\s*guys\b|\bfive guys\b',            'Five Guys'),
    (r'\btj\'?s pizza\b',                      "TJ's Pizza"),
    (r'\bpanera\b',                            'Panera Bread'),
    (r'\bpapa john',                           "Papa John's"),
    (r'\bbob evans\b',                         'Bob Evans'),
    (r'\bred lobster\b',                       'Red Lobster'),
    (r'\bcheesecake\b',                        'Cheesecake Factory'),
    (r'\bdairy queen\b',                       'Dairy Queen'),
    (r'\bdoordash\b',                          'DoorDash'),
    (r'\blees chicken\b',                      "Lee's Chicken"),
    # Home improvement / retail
    (r'\btj\s*maxx\b|\btjx\b',                 'TJ Maxx'),
    (r'\blowes\b',                             "Lowe's"),
    (r'\bmenards\b|\bmnrd\b',                  'Menards'),
    (r'\bharbor freight\b',                    'Harbor Freight'),
    (r'\bhobby.lobby\b',                       'Hobby Lobby'),
    (r'\bjcpenney\b',                          'JCPenney'),
    (r'\btractor.supply\b',                    'Tractor Supply'),
    (r'\bsherwin.williams\b',                  'Sherwin-Williams'),
    (r'\bgoodwill\b',                          'Goodwill'),
    (r'\bbuild.a.bear\b',                      'Build-A-Bear'),
    # Pharmacy / health
    (r'\bwalgreens\b',                         'Walgreens'),
    (r'\bcvs\b',                               'CVS'),
    # Gas / convenience
    (r'\bclark\b',                             'Clark Gas'),
    (r'\bcircle k\b',                          'Circle K'),
    (r'\bshell\b',                             'Shell'),
    (r'\bspeedway\b',                          'Speedway'),
    (r'\bbuc.ee',                              "Buc-ee's"),
    # Financial
    (r'\bcapital one\b',                       'Capital One'),
    (r'\bcomenity\b',                          'Comenity'),
    (r'\bchase credit',                        'Chase Credit Card'),
    (r'\bbarclay',                             'Barclays'),
    (r'\bsyncb\b',                             'Synchrony Bank'),
    (r'\bsynchrony\b',                         'Synchrony Bank'),
    (r'\bonemain\b',                           'OneMain Financial'),
    (r'\bcash app\b',                          'Cash App'),
    (r'\bvenmo\b',                             'Venmo'),
    (r'\bzelle\b',                             'Zelle'),
    (r'\bgofndme\b|\bgofundme\b',              'GoFundMe'),
    # Payroll / employment
    # Auto
    (r'\bford motor cr\b|\bford motor credit\b','Ford Motor Credit'),
    (r'\bstellantis',                          'Stellantis Lease'),
    # Utilities / telecom
    (r'\baep\b',                               'AEP Ohio Power'),
    (r'\benbridge\b',                          'Enbridge Gas'),
    (r'\bspectrum\b',                          'Spectrum'),
    (r'\bat\s*&?\s*t\b|\batt\b',               'AT&T'),
    (r'\bverizon\b',                           'Verizon'),
    (r'\bt-?mobile\b',                         'T-Mobile'),
    # Insurance
    (r'\bgeico\b',                             'GEICO'),
    (r'\bnationwide\s+pet',                    'Nationwide Pet Insurance'),
    (r'^nationwide$',                          'Nationwide'),
    (r'\bprogressive\b',                       'Progressive'),
    (r'\ballstate\b',                          'Allstate'),
    (r'\bstate farm\b',                        'State Farm'),
    # Online / subscriptions
    (r'\bamazon\b|\bamzn\b',                   'Amazon'),
    (r'\bapplecard\b',                         'Apple Card'),
    (r'\bapple cash\b',                        'Apple Cash'),
    (r'\bapple\.com',                          'Apple'),
    (r'\banthropic\b',                         'Anthropic'),
    (r'\bcricut\b',                            'Cricut'),
    (r'\bnetflix\b',                           'Netflix'),
    (r'\bdisney(?:plus|\+)?\b',                'Disney+'),
    (r'\bstarz\b',                             'Starz'),
    (r'\bspotify\b',                           'Spotify'),
    (r'\bhulu\b',                              'Hulu'),
    (r'\brocket money\b',                      'Rocket Money'),
    (r'\bchewy\b',                             'Chewy'),
    (r'\bpetco\b',                             'Petco'),
    # Local / Millbrook OH-specific
    (r'\bcity of millbrook\b',                      'City of Millbrook'),
    (r'\bdept\s+education\b|\bdoe\b',          'Dept of Education'),
    (r'\bresource recycl',                     'Resource Recycling'),
    (r'\bspring and mai',                      'Spring and Main'),
    (r'\bthe met\b',                           'The Met'),
    (r'\bindian lake\b',                       'Indian Lake Outfitters'),
]
_MERCHANT_MAP = [(_re.compile(p, _re.I), n) for p, n in _MERCHANT_MAP]

def _canonicalize_merchant(raw):
    """
    Two-stage canonicalization. Strip generic noise first, then check the
    brand dictionary. Falls back to title-case for unmatched all-caps
    strings (most banks emit ALL CAPS), or the stripped raw string
    otherwise. Returns the input unchanged if it's already empty.
    """
    if not raw:
        return raw
    stripped = _strip_noise(raw)
    for pat, name in _MERCHANT_MAP:
        if pat.search(stripped):
            return name
    # No dict hit. Make the noise-stripped string readable.
    if stripped and stripped.isupper() and 3 <= len(stripped) <= 40:
        return stripped.title()
    return stripped or raw


# ── Bank signatures ───────────────────────────────────────────────────────────
# Each signature describes how to read a specific bank/card export.
# 'headers' — lowercase column names that must ALL be present for a match.
# 'date' / 'description' — column names to pull from.
# 'amount' — single signed-amount column (positive=credit, negative=debit), OR
# 'debit' / 'credit' — separate unsigned columns.
# 'category' — optional column holding the bank's own category label.

BANK_SIGNATURES = [
    {
        'name': 'Chase',
        'headers': {'details', 'posting date', 'description', 'amount', 'type'},
        'date': 'posting date', 'description': 'description', 'amount': 'amount',
        'category': None,
    },
    {
        'name': 'Bank of America',
        'headers': {'date', 'description', 'amount', 'running bal.'},
        'date': 'date', 'description': 'description', 'amount': 'amount',
        'category': None,
    },
    {
        'name': 'Capital One',
        'headers': {'transaction date', 'posted date', 'description', 'debit', 'credit'},
        'date': 'transaction date', 'description': 'description',
        'debit': 'debit', 'credit': 'credit', 'category': 'category',
    },
    {
        'name': 'Discover',
        'headers': {'trans. date', 'post date', 'description', 'amount', 'category'},
        'date': 'trans. date', 'description': 'description', 'amount': 'amount',
        'category': 'category',
    },
    {
        'name': 'Citi',
        'headers': {'status', 'date', 'description', 'debit', 'credit'},
        'date': 'date', 'description': 'description',
        'debit': 'debit', 'credit': 'credit', 'category': None,
    },
    {
        'name': 'US Bank',
        'headers': {'date', 'transaction', 'name', 'memo', 'amount'},
        'date': 'date', 'description': 'name', 'amount': 'amount',
        'category': None,
    },
    {
        'name': 'PNC',
        'headers': {'date', 'description', 'amount', 'balance'},
        'date': 'date', 'description': 'description', 'amount': 'amount',
        'category': None,
    },
    {
        # Superior Credit Union export shape:
        # Account Number, Suffix, Type, Name, Transaction Date,
        # Transaction Description, Transaction Amount, Running Balance,
        # Transaction Type, Check Number, Notes, Tags
        #
        # Distinctive subset (avoids 'name'/'type' colliding with other
        # signatures' generic column names): the four 'transaction *' columns
        # together only appear in this export. 'name' here is the ACCOUNT
        # name (e.g. "STANDARD CHECKING"), not the transaction description —
        # that's column 'transaction description'. Without this explicit
        # signature, this export falls through to _parse_generic(), whose
        # desc/payee/name/memo heuristic matches the literal 'name' column
        # before it ever reaches 'transaction description', so every single
        # row's description becomes the account name instead of the actual
        # transaction.
        'name': 'Superior Credit Union',
        'headers': {'transaction date', 'transaction description',
                     'transaction amount', 'transaction type'},
        'date': 'transaction date', 'description': 'transaction description',
        'amount': 'transaction amount', 'balance': 'running balance',
        'category': None, 'rich_description': True,
    },
    {
        # Apple Card export shape: Transaction Date, Clearing Date,
        # Description, Merchant, Category, Type, Amount (USD), Purchased By.
        # Confirmed against a real export (July 2026) — previously had no
        # dedicated signature at all, so every Apple Card file fell through
        # to _parse_generic(), which sometimes couldn't recognize the
        # column layout ("could not recognize column layout" error), and
        # even when it did fall back successfully, got the sign backwards.
        #
        # Apple Card's Amount (USD) column uses the OPPOSITE sign
        # convention from a typical checking-account export: a charge that
        # INCREASES what you owe is POSITIVE (e.g. "INTEREST CHARGE" = 45.96),
        # and a payment that DECREASES what you owe is NEGATIVE (e.g. an ACH
        # payment = -71). The generic amount handling elsewhere in this file
        # assumes positive = credit, negative = debit — backwards for this
        # format — hence 'invert_amount_sign' below.
        'name': 'Apple Card',
        'headers': {'transaction date', 'clearing date', 'merchant',
                     'amount (usd)', 'purchased by'},
        'date': 'transaction date', 'description': 'description',
        'amount': 'amount (usd)', 'category': 'category',
        'invert_amount_sign': True,
    },
]


def _find_header_row(rows):
    """
    Scan the first few rows for one that looks like a CSV header — i.e.
    contains a recognizable 'date' or 'description'-style column name.
    Some banks (Bank of America) prepend a few summary lines before the
    real header. Returns (header_cells, row_index) or (None, -1).
    """
    scan_limit = min(len(rows), 10)
    for i in range(scan_limit):
        cells = [c.strip().lower() for c in rows[i]]
        if not any(cells):
            continue
        has_date = any('date' in c for c in cells)
        has_desc = any(c in ('description', 'name', 'payee', 'memo', 'transaction') for c in cells)
        if has_date and has_desc:
            return rows[i], i
    return None, -1


def _match_signature(headers_lower: set):
    for sig in BANK_SIGNATURES:
        if sig['headers'].issubset(headers_lower):
            return sig
    return None


def _col_index(header_row, name):
    lower = [h.strip().lower() for h in header_row]
    return lower.index(name) if name in lower else -1


def _parse_with_signature(data_rows, header_row, sig, warnings):
    records = []
    date_i  = _col_index(header_row, sig['date'])
    desc_i  = _col_index(header_row, sig['description'])
    cat_i   = _col_index(header_row, sig['category']) if sig.get('category') else -1
    bal_i   = _col_index(header_row, sig['balance'])  if sig.get('balance')  else -1

    amt_i   = _col_index(header_row, sig['amount']) if sig.get('amount') else -1
    dbt_i   = _col_index(header_row, sig['debit'])  if sig.get('debit')  else -1
    crd_i   = _col_index(header_row, sig['credit']) if sig.get('credit') else -1

    skipped = 0
    for row in data_rows:
        if not row or not any(row):
            continue
        try:
            iso_date = _parse_date(row[date_i]) if date_i >= 0 and date_i < len(row) else None
            desc     = row[desc_i].strip() if desc_i >= 0 and desc_i < len(row) else ''
        except IndexError:
            skipped += 1
            continue

        if not iso_date or not desc:
            skipped += 1
            continue

        amount = None
        txn_type = 'debit'

        if amt_i >= 0 and amt_i < len(row):
            a = _parse_amount(row[amt_i])
            if a is not None and a != 0:
                # BUG FIX (July 6): most signed-amount exports use
                # positive = money in (credit), negative = money out (debit)
                # — but some credit-card exports (confirmed: Apple Card) use
                # the opposite convention, since they're reporting the
                # change to what you OWE rather than a checking-account-
                # style balance: a charge that increases your balance owed
                # is positive, a payment that decreases it is negative.
                # Signatures opt into this via 'invert_amount_sign'; every
                # other signature is unaffected (defaults to the original
                # behavior).
                if sig.get('invert_amount_sign'):
                    txn_type = 'debit' if a > 0 else 'credit'
                else:
                    txn_type = 'credit' if a > 0 else 'debit'
                amount = abs(a)
        else:
            d_val = _parse_amount(row[dbt_i]) if dbt_i >= 0 and dbt_i < len(row) else None
            c_val = _parse_amount(row[crd_i]) if crd_i >= 0 and crd_i < len(row) else None
            if c_val and c_val > 0:
                amount = c_val
                txn_type = 'credit'
            elif d_val and d_val != 0:
                amount = abs(d_val)
                txn_type = 'debit'

        if amount is None or amount <= 0:
            skipped += 1
            continue

        raw_cat = row[cat_i].strip() if cat_i >= 0 and cat_i < len(row) else ''

        # CP3 — when the signature opts in, pull true date / MCC / card
        # last-4 / cleaned merchant out of the description. `date` becomes
        # the TRUE transaction date when one was found; `posted_date` always
        # holds what the bank's own date column said (decision #2 — store
        # both). MCC (when present) takes priority for categorization.
        mcc = card_last4 = merchant = None
        true_date = None
        if sig.get('rich_description'):
            rich = parse_rich_description(desc)
            true_date  = rich['true_date']
            mcc        = rich['mcc']
            card_last4 = rich['card_last4']
            merchant   = rich['merchant']

        record = {
            'date':         true_date or iso_date,
            'posted_date':  iso_date,
            'description':  desc,
            'amount':       round(amount, 2),
            'type':         txn_type,
            'category':     auto_category(desc, mcc) if not raw_cat else auto_category(desc, mcc),
            'raw_category': raw_cat,
            'cleared':      True,
        }
        if merchant:
            record['merchant'] = merchant
        if mcc:
            record['mcc'] = mcc
        if card_last4:
            record['card_last4'] = card_last4
        if bal_i >= 0 and bal_i < len(row):
            bal = _parse_amount(row[bal_i])
            if bal is not None:
                record['running_balance'] = round(bal, 2)

        # Check number — present in some bank exports (paper checks).
        # Look for a 'check number' or 'check #' or 'check_number' column.
        check_i = _col_index(header_row, 'check number')
        if check_i < 0: check_i = _col_index(header_row, 'check #')
        if check_i < 0: check_i = _col_index(header_row, 'check_number')
        if check_i >= 0 and check_i < len(row):
            raw_check = row[check_i].strip().lstrip('0')  # strip leading zeros
            if raw_check and raw_check not in ('0', ''):
                record['check_number'] = raw_check

        records.append(record)

    if skipped:
        warnings.append(f'{skipped} row(s) skipped (missing date, description, or amount)')

    return records


def _parse_generic(data_rows, header_row, warnings):
    """
    Fallback for unrecognized formats. Finds the most likely date,
    description, and amount columns by substring match — mirrors
    clientParseCSV() in app.js.
    """
    headers = [h.strip().lower() for h in header_row]

    date_i = next((i for i, h in enumerate(headers) if 'date' in h), -1)
    # Prefer an actual description column first. Only fall back to
    # payee/memo/name if there's no 'desc' column at all — a bare 'name'
    # column (as in Superior Credit Union's export) is usually the ACCOUNT
    # name, not the transaction description, so it must lose to a real
    # 'description' column when both exist.
    desc_i = next((i for i, h in enumerate(headers) if 'desc' in h), -1)
    if desc_i < 0:
        desc_i = next((i for i, h in enumerate(headers)
                        if any(k in h for k in ('payee', 'memo', 'name'))), -1)
    amt_i  = next((i for i, h in enumerate(headers) if 'amount' in h or 'amt' in h), -1)
    dbt_i  = next((i for i, h in enumerate(headers) if 'debit' in h or 'withdrawal' in h), -1)
    crd_i  = next((i for i, h in enumerate(headers) if 'credit' in h or 'deposit' in h), -1)
    cat_i  = next((i for i, h in enumerate(headers) if 'category' in h), -1)

    if date_i < 0:
        date_i = 0
    if desc_i < 0:
        desc_i = 1 if len(headers) > 1 else 0

    records = []
    skipped = 0
    for row in data_rows:
        if not row or not any(row):
            continue
        try:
            iso_date = _parse_date(row[date_i]) if date_i < len(row) else None
            desc     = row[desc_i].strip() if desc_i < len(row) else ''
        except IndexError:
            skipped += 1
            continue

        if not iso_date or not desc:
            skipped += 1
            continue

        amount = None
        txn_type = 'debit'

        if amt_i >= 0 and amt_i < len(row):
            a = _parse_amount(row[amt_i])
            if a is not None and a != 0:
                txn_type = 'credit' if a > 0 else 'debit'
                amount = abs(a)
        else:
            d_val = _parse_amount(row[dbt_i]) if dbt_i >= 0 and dbt_i < len(row) else None
            c_val = _parse_amount(row[crd_i]) if crd_i >= 0 and crd_i < len(row) else None
            if c_val and c_val > 0:
                amount = c_val
                txn_type = 'credit'
            elif d_val and d_val != 0:
                amount = abs(d_val)
                txn_type = 'debit'

        if amount is None or amount <= 0:
            skipped += 1
            continue

        raw_cat = row[cat_i].strip() if cat_i >= 0 and cat_i < len(row) else ''

        records.append({
            'date':         iso_date,
            'description':  desc,
            'amount':       round(amount, 2),
            'type':         txn_type,
            'category':     auto_category(desc),
            'raw_category': raw_cat,
            'cleared':      True,
        })

    if skipped:
        warnings.append(f'{skipped} row(s) skipped (missing date, description, or amount)')

    return records


def _parse_wells_fargo(rows, warnings):
    """
    Wells Fargo CSVs have NO header row. Column order is fixed:
        Date, Amount, *, *, Description
    Amount is signed (negative = debit, positive = credit).
    """
    records = []
    skipped = 0
    for row in rows:
        if not row or not any(row):
            continue
        if len(row) < 5:
            skipped += 1
            continue

        iso_date = _parse_date(row[0])
        amount   = _parse_amount(row[1])
        desc     = row[4].strip()

        if not iso_date or amount is None or amount == 0 or not desc:
            skipped += 1
            continue

        records.append({
            'date':         iso_date,
            'description':  desc,
            'amount':       round(abs(amount), 2),
            'type':         'credit' if amount > 0 else 'debit',
            'category':     auto_category(desc),
            'raw_category': '',
            'cleared':      True,
        })

    if skipped:
        warnings.append(f'{skipped} row(s) skipped (unrecognized format)')

    return records


def _looks_like_wells_fargo(rows):
    """
    Heuristic: first row has 5+ columns, column 0 parses as a date,
    and column 1 parses as a signed number — and there's no recognizable
    header row.
    """
    if not rows or not rows[0] or len(rows[0]) < 5:
        return False
    return (_parse_date(rows[0][0]) is not None
            and _parse_amount(rows[0][1]) is not None)


# ── OFX / QFX parsing ──────────────────────────────────────────────────────
# OFX 1.x is SGML, not XML — tags don't self-close, and many writers omit
# closing tags entirely (the tag remains open until the next sibling tag
# starts, just like HTML <p>). XML parsers will choke on this. Rather than
# pull in a heavy ofxparse dependency, do it directly with regex over the
# specific tags we need. This is robust enough for every QFX/OFX file the
# big banks emit; we don't care about full SGML compliance.

_OFX_TAG_RE = re.compile(r'<([A-Z][A-Z0-9.]*)>([^<\r\n]*)', re.IGNORECASE)
_OFX_TRN_RE = re.compile(r'<STMTTRN>(.*?)</STMTTRN>', re.IGNORECASE | re.DOTALL)


def _ofx_field(block: str, name: str) -> str:
    """Extract a single SGML field value from a block (case-insensitive)."""
    m = re.search(rf'<{name}>([^<\r\n]*)', block, re.IGNORECASE)
    if not m:
        return ''
    return m.group(1).strip()


def _parse_ofx_date(s: str):
    """OFX dates are YYYYMMDD or YYYYMMDDHHMMSS, optionally with [TZ]."""
    if not s:
        return None
    # Strip timezone tail like '20260618120000.000[-5:EST]'
    s = re.split(r'[\[.]', s, 1)[0].strip()
    if len(s) < 8:
        return None
    try:
        return datetime.strptime(s[:8], '%Y%m%d').date()
    except ValueError:
        return None


def _parse_ofx(text: str, warnings: list):
    """Parse OFX 1.x SGML or OFX 2.x XML body into Groundwork records.

    The two format variants share tag names so the same regex extraction
    works on both. We only care about <STMTTRN> blocks under <BANKMSGSRSV1>
    (bank) or <CREDITCARDMSGSRSV1> (credit card) — investment OFX uses a
    completely different schema and would need its own handler.

    OFX doesn't provide a running balance per transaction (unlike CSV
    exports from the same bank). It does provide a LEDGERBAL — the account
    balance as of the export date. We use that as an anchor and walk
    backward to calculate what the balance was after each prior transaction.
    """
    # Detect institution name for the bank label
    org = _ofx_field(text, 'ORG') or 'OFX/QFX'

    txn_blocks = _OFX_TRN_RE.findall(text)
    if not txn_blocks:
        warnings.append('No <STMTTRN> transactions found in OFX file')
        return [], org, warnings

    # Extract LEDGERBAL — the account balance as of the export date.
    # This is the anchor we use to back-calculate per-row running balances.
    ledger_bal = None
    bal_match = re.search(r'<LEDGERBAL>.*?<BALAMT>([^<\r\n]+)', text, re.IGNORECASE | re.DOTALL)
    if bal_match:
        try:
            ledger_bal = round(float(bal_match.group(1).strip()), 2)
        except ValueError:
            pass

    records = []
    skipped = 0
    for block in txn_blocks:
        date = _parse_ofx_date(_ofx_field(block, 'DTPOSTED'))
        amt_raw = _ofx_field(block, 'TRNAMT')
        if not date or not amt_raw:
            skipped += 1
            continue
        try:
            amt = float(amt_raw)
        except ValueError:
            skipped += 1
            continue

        name_field = _ofx_field(block, 'NAME')
        memo_field = _ofx_field(block, 'MEMO')
        description = memo_field or name_field

        ttype = 'credit' if amt >= 0 else 'debit'
        fitid = _ofx_field(block, 'FITID')

        rich = parse_rich_description(description)

        rec = {
            'date':         date.isoformat(),
            'description':  description,
            'amount':       abs(amt),
            'type':         ttype,
            'category':     auto_category(description, rich.get('mcc', '') or ''),
            'raw_category': '',
            'cleared':      True,
            'merchant':     rich['merchant'],
            'mcc':          rich['mcc'],
            'card_last4':   rich['card_last4'],
            'posted_date':  date.isoformat(),
            'fitid':        fitid,
            'source':       'qfx',
            '_amt_signed':  amt,  # keep signed amount for balance walk
        }
        if rich['true_date']:
            rec['date'] = rich['true_date']

        records.append(rec)

    if skipped:
        warnings.append(f'Skipped {skipped} OFX transactions with missing date or amount')

    # ── Back-calculate running balances from LEDGERBAL ─────────────────
    # OFX files carry the account balance once at the top (LEDGERBAL),
    # not per row. Sort records by date ascending, then walk backward from
    # the anchor (most recent transaction = ledger_bal) to calculate what
    # the balance was after each prior transaction.
    #
    # "Thumans Home Imp" (last row, most recent) → $3,163.58 (LEDGERBAL)
    # The row before it → $3,163.58 + $1,932.56 (reversed the debit) = $5,096.14
    # ...and so on backward to the oldest row.
    if ledger_bal is not None and records:
        # Sort by date asc, then by position in file (stable) for same-day txns
        records.sort(key=lambda r: r['date'])
        # Anchor: the last (most recent) record gets the ledger balance
        running = ledger_bal
        records[-1]['running_balance'] = running
        # Walk backward
        for i in range(len(records) - 2, -1, -1):
            next_rec = records[i + 1]
            signed   = next_rec['_amt_signed']
            running  = running - signed   # invert: undo the next transaction
            records[i]['running_balance'] = round(running, 2)

    # Clean up the internal field before returning
    for rec in records:
        rec.pop('_amt_signed', None)

    return records, org, warnings


# ── QIF parsing ────────────────────────────────────────────────────────────
# QIF is line-oriented: each line starts with a single-letter code followed
# by the field value. Transactions are terminated by a line containing just
# '^'. The !Type:Bank header tells us this is checking/savings (vs !Type:CCard
# for credit card, !Type:Cash, !Type:Invst — we treat all the cash-like ones
# the same way).
#
# Field codes we care about:
#   D — date (M/D/YY, M/D/YYYY, or YYYY-M-D)
#   T — amount (signed)
#   P — payee
#   M — memo
#   N — check number or transaction ref
#   C — cleared marker (* or X = cleared)
#   L — category (often in [Brackets] for transfers)

_QIF_DATE_FORMATS = ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', "%m/%d'%Y", "%m/%d'%y"]


# ── QIF/Quicken category normalization ──────────────────────────────────────
# Quicken's own category vocabulary ("Auto & Transport", "Mortgage & Rent",
# "Bills & Utilities", ...) almost never exactly matches Groundwork's tree —
# bank_import_commit() in server.py does an exact case-insensitive match
# against the existing taxonomy and safely falls back to "Other" for
# anything that doesn't match (it never creates a stray category), so an
# unmapped Quicken label was always safe, just under-categorized. This
# bridges the common Quicken/Money default categories to Groundwork's
# current tree (core/database.py :: CATEGORY_TREE) so QIF imports land in
# real categories instead of mostly "Other".
_QIF_CATEGORY_MAP = {
    'auto & transport':     'Transportation', 'auto insurance':    'Auto Insurance',
    'auto payment':         'Transportation', 'gas & fuel':        'Gas / Fuel',
    'parking':              'Parking / Tolls', 'parking & tolls':  'Parking / Tolls',
    'public transportation':'Rideshare / Transit', 'ride share':   'Rideshare / Transit',
    'service & parts':      'Car Maintenance', 'auto maintenance': 'Car Maintenance',

    'bills & utilities': 'Utilities', 'mobile phone': 'Phone / Cell',
    'cell phone':        'Phone / Cell', 'cable/satellite': 'Cable / TV', 'cable': 'Cable / TV',
    'internet':          'Internet', 'utilities': 'Utilities', 'electric': 'Electric',
    'electricity':       'Electric', 'water': 'Water / Sewer', 'trash': 'Trash',

    'food & dining': 'Food', 'groceries': 'Groceries', 'restaurants': 'Restaurants',
    'fast food':     'Fast Food / Takeout', 'coffee shops': 'Coffee Shops',
    'alcohol & bars':'Restaurants', 'dining': 'Restaurants',

    'health & fitness': 'Healthcare', 'doctor': 'Doctor / Co-pays',
    'dentist':          'Dental', 'pharmacy': 'Prescriptions', 'gym': 'Gym / Fitness',
    'health insurance': 'Health Insurance', 'vision': 'Vision',

    'home': 'Home', 'mortgage & rent': 'Rent / Mortgage', 'rent': 'Rent / Mortgage',
    'mortgage':        'Rent / Mortgage', 'home improvement': 'Home Improvement',
    'home insurance':  "Homeowner's Insurance", 'home services': 'Home Maintenance',
    'furnishings':     'Furniture / Decor', 'lawn & garden': 'Lawn / Landscaping',

    'shopping': 'Personal', 'clothing': 'Clothing', 'hobbies': 'Hobbies',
    'personal care': 'Personal Care', 'hair': 'Haircut / Salon',
    'spa & massage': 'Personal Care',

    'entertainment': 'Entertainment', 'movies & dvds': 'Activities / Events',
    'music':          'Streaming Music', 'amusement': 'Activities / Events',
    'arts':           'Activities / Events', 'streaming': 'Streaming Video',

    'education': 'Education', 'books & supplies': 'Books / Materials',
    'tuition':   'Tuition / Courses', 'student loan': 'Debt',

    'gifts & donations': 'Gifts & Donations', 'charity': 'Charitable Donations',
    'gift': 'Gifts',

    'fees & charges': 'Interest / Fees', 'bank fees': 'Interest / Fees',
    'finance charge': 'Interest / Fees', 'late fee': 'Interest / Fees',
    'service fee':    'Interest / Fees', 'interest': 'Interest / Fees',

    'income': 'Income', 'paycheck': 'Paycheck / Salary', 'salary': 'Paycheck / Salary',
    'bonus':  'Side Income', 'interest income': 'Side Income',
    'dividend': 'Side Income', 'reimbursement': 'Side Income',
    'rental income': 'Rental Income',

    'transfer': 'Transfer', 'credit card payment': 'Debt',
    'transfer for cash spending': 'Transfer', 'balance adjustments': 'Transfer',
    'investments': 'Transfer', 'withdrawal': 'Transfer', 'deposit': 'Transfer',

    'insurance': 'Insurance', 'life insurance': 'Life Insurance',

    'taxes': 'Property Taxes', 'property tax': 'Property Taxes',

    'loan': 'Debt', 'loan interest': 'Interest / Fees', 'loan payment': 'Debt',

    'pets': 'Pets', 'pet food & supplies': 'Pet Food / Supplies',
    'veterinary': 'Vet / Medical',

    'travel': 'Vacation / Travel', 'air travel': 'Vacation / Travel',
    'hotel': 'Vacation / Travel', 'rental car': 'Vacation / Travel',
    'vacation': 'Vacation / Travel',
}


def normalize_qif_category(raw: str) -> str:
    """
    Map a Quicken category label to the closest current Groundwork category
    name. Handles QIF's "Parent:Child" subcategory syntax by trying the
    child first, then the parent. Returns the raw string UNCHANGED (never a
    guess, never blanked) when nothing matches — bank_import_commit()'s
    exact-match-or-Other fallback in server.py already handles that case
    safely, so an unmapped label is no worse off than before this function
    existed.
    """
    if not raw:
        return raw
    key = raw.strip().lower()
    if ':' in key:
        parent, _, child = key.partition(':')
        if child in _QIF_CATEGORY_MAP:
            return _QIF_CATEGORY_MAP[child]
        if parent in _QIF_CATEGORY_MAP:
            return _QIF_CATEGORY_MAP[parent]
        key = child
    return _QIF_CATEGORY_MAP.get(key, raw)


def _parse_qif_date(s: str):
    """QIF dates come in many flavors — try each one in order."""
    if not s:
        return None
    # Quicken's 2000-era apostrophe format: "1/15'25" means 1/15/2025
    s = s.strip().replace(' ', '')
    for fmt in _QIF_DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt).date()
            # %y gives 1999 for "00" sometimes; nudge into the 21st century
            if d.year < 1950:
                d = d.replace(year=d.year + 100)
            return d
        except ValueError:
            continue
    return None


def _parse_qif(text: str, warnings: list):
    """Parse a QIF file's transaction list into Groundwork records.

    QIF files can hold multiple accounts in one file (separated by
    !Account / !Type:Bank headers); we flatten them all into one record
    list since Groundwork tracks accounts at the transaction level.
    """
    records = []
    skipped = 0
    current = {}
    # A bare "!Account" header introduces an account-definition block (name,
    # type, description) before that account's transactions — its N<name>/
    # T<type> field lines share letter codes with real transaction fields
    # (T is also the amount field), so they must be tracked and skipped
    # explicitly rather than folded into `current`, or the account block's
    # own '^' terminator gets misread as a dateless, amount-less transaction.
    in_account_header = False

    for line in text.splitlines():
        line = line.rstrip('\r')
        if not line:
            continue
        if line.startswith('!Account'):
            in_account_header = True
            continue
        if line.startswith('!Type:'):
            in_account_header = False
            continue
        if line.startswith('!'):
            continue
        if in_account_header:
            if line == '^':
                in_account_header = False
            continue
        if line == '^':
            # End of transaction — flush it
            if current:
                date = _parse_qif_date(current.get('D', ''))
                amt_raw = current.get('T', '').replace(',', '').replace('$', '')
                try:
                    amt = float(amt_raw) if amt_raw else None
                except ValueError:
                    amt = None
                if date and amt is not None:
                    description = current.get('P', '') or current.get('M', '')
                    memo = current.get('M', '')
                    if memo and memo != description:
                        description = f'{description} {memo}'.strip()
                    ttype = 'credit' if amt >= 0 else 'debit'
                    cleared = current.get('C', '').strip().upper() in ('*', 'X', 'R')
                    raw_cat = current.get('L', '')
                    # Strip transfer brackets — "[Savings]" becomes "Savings"
                    if raw_cat.startswith('[') and raw_cat.endswith(']'):
                        raw_cat = raw_cat[1:-1]
                    mapped_cat = normalize_qif_category(raw_cat) if raw_cat else ''
                    rich = parse_rich_description(description)
                    rec = {
                        'date':         date.isoformat(),
                        'description':  description,
                        'amount':       abs(amt),
                        'type':         ttype,
                        'category':     mapped_cat or auto_category(description, rich.get('mcc', '') or ''),
                        'raw_category': raw_cat,
                        'cleared':      cleared,
                        'merchant':     rich['merchant'],
                        'mcc':          rich['mcc'],
                        'card_last4':   rich['card_last4'],
                        'posted_date':  date.isoformat(),
                        'source':       'qif',
                    }
                    if rich['true_date']:
                        rec['date'] = rich['true_date']
                    records.append(rec)
                else:
                    skipped += 1
            current = {}
            continue
        # Field line: first char is the code, rest is the value
        code = line[0]
        value = line[1:].strip()
        current[code] = value

    if skipped:
        warnings.append(f'Skipped {skipped} QIF transactions with missing date or amount')

    return records, 'Quicken QIF', warnings


# ── Public API ─────────────────────────────────────────────────────────────

def detect_and_parse(text: str, filename: str = ''):
    """
    Detect the file format and parse transactions.

    Returns: (records, bank_name, warnings)
    """
    warnings = []

    # Normalize line endings and strip BOM
    text = text.lstrip('\ufeff')

    # ── Format detection by content shape, not by file extension. The
    # extension might lie (a .txt holding CSV, a .csv that's actually OFX)
    # but the content signature is reliable.
    head = text[:200].lstrip().upper()
    if head.startswith('OFXHEADER:') or head.startswith('<OFX>') or '<?XML' in head[:50] and '<OFX>' in text[:600].upper():
        return _parse_ofx(text, warnings)
    if head.startswith('!TYPE:'):
        return _parse_qif(text, warnings)

    # Fall through to CSV (with .txt aliasing — they're identical to the parser)
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(c.strip() for c in r)]

    if not rows:
        return [], 'Unknown', ['File appears to be empty']

    header_row, header_idx = _find_header_row(rows)

    if header_row is not None:
        headers_lower = {c.strip().lower() for c in header_row}
        data_rows = rows[header_idx + 1:]

        sig = _match_signature(headers_lower)
        if sig:
            records = _parse_with_signature(data_rows, header_row, sig, warnings)
            return records, sig['name'], warnings

        records = _parse_generic(data_rows, header_row, warnings)
        bank = 'Generic CSV'
        if not records:
            warnings.append('Could not recognize column layout — try a different export format')
        return records, bank, warnings

    # No recognizable header — try Wells Fargo's headerless layout
    if _looks_like_wells_fargo(rows):
        records = _parse_wells_fargo(rows, warnings)
        return records, 'Wells Fargo', warnings

    return [], 'Unknown', ['Could not detect a date/description header row in this file']


def get_category_summary(records) -> dict:
    """Returns { category_name: count } for the category breakdown UI."""
    summary = {}
    for r in records:
        cat = r.get('category', 'Other') or 'Other'
        summary[cat] = summary.get(cat, 0) + 1
    return summary
