"""The necessity floor, version 3 (gw 2.0/FLOOR_V3.md, item 47 = item 45 H2; Rob 2026-10-08: "Expand the list to cover
the identified health terms and built-in categories. Test aliases, capitalization, partial matches, and false
positives. A match inside an unrelated word, such as `ER` inside `water`, must not count as valid classification.").

    F1  every health name item 45 found missing is protected now, under its common aliases and in any capitalisation
    F2  a term inside an unrelated word never counts; a name inside a longer term never counts
    F3  every built-in category keeps its verdict, except Long-term Care (now protected, intended) and Rental Income
        (an income category, no longer matched by "rent" inside "rental")
    F4  the version is 3, and every verdict carries it
"""


def run(ctx):
    check = ctx.check
    from core import solution as s
    from core.database import CATEGORY_TREE

    p = s.is_protected

    aliases = ['Medicine', 'Medicines', 'Meds', 'Rx', 'RX', 'Insulin', 'Urgent Care', 'urgent care visit', 'Physician',
               'Pediatrician', 'Surgery', 'Surgeon', 'Ambulance', 'OB/GYN', 'OB-GYN', 'OBGYN', 'Labs', 'Lab Work',
               'Hearing Aids', 'Hearing', 'Glasses', 'Eyeglasses', 'Contacts', 'Contact Lenses', 'Optometrist',
               'Ophthalmologist', 'Orthodontist', 'Orthodontics', 'Braces', 'Long-term Care', 'Long Term Care',
               'Nursing Home', 'Home Health', 'ER', 'Emergency Room', 'ER visit', 'Electricity', 'Grocery', 'Gasoline']
    check('s159 F1 every health name item 45 found missing is protected, under its aliases',
          [n for n in aliases if not p(n)] == [])
    check('s159 F1 capitalisation and plurals do not change the verdict',
          all(p(n) for n in ('PRESCRIPTIONS', 'prescription', 'Prescriptions', 'MEDS', 'med', 'doctors', 'Doctor')))
    check('s159 F1 a name that carries a floor term among other words is protected ("CVS Pharmacy", "Doctor / Co-pays")',
          all(p(n) for n in ('CVS Pharmacy', "St. Mary's Hospital", 'Doctor / Co-pays', 'Kids Activities', 'Water / Sewer')))

    accidents = ['Hospitality', 'Doctorate', 'Parenting', 'Current Expenses', 'Transporter', 'Watercolor', 'Paper Goods',
                 'Laboratory Equipment', 'Medallion', 'Gaming', 'Seafood', 'Kidsports', 'Rental Car', 'Parental Gifts',
                 'Entertainment', 'Home', 'Dining Out', 'Shopping', 'Gym / Fitness', 'Personal Care']
    check('s159 F2 a term inside an unrelated word never counts ("ER" in "water", "hospital" in "Hospitality", '
          '"rent" in "Parenting", "lab" in "Laboratory")', [n for n in accidents if p(n)] == [])
    check('s159 F2 a name inside a longer term never counts ("Home" is not "nursing home")',
          not p('Home') and not p('Room') and not p('Pay'))

    def old(n):                      # version 2's matching, on version 2's terms, for the comparison only
        n = n.strip().lower()
        return any(t in n or n in t for t in s.NECESSITY_FLOOR[:44])
    changed = sorted((r[0], p(r[0])) for r in CATEGORY_TREE if p(r[0]) != old(r[0]))
    check('s159 F3 every built-in keeps its verdict except Long-term Care (now protected) and Rental Income (income)',
          changed == [('Long-term Care', True), ('Rental Income', False)])
    check('s159 F3 every built-in health and necessity category is protected',
          all(p(n) for n in ('Healthcare', 'Doctor / Co-pays', 'Prescriptions', 'Dental', 'Vision', 'Health Insurance',
                             'Rent / Mortgage', 'Utilities', 'Electric', 'Gas', 'Water / Sewer', 'Groceries',
                             'Gas / Fuel', 'Childcare / Daycare', 'Long-term Care')))

    check('s159 F4 the floor is version 3', s.NECESSITY_FLOOR_VERSION == '3')
    v = s._overspend([{'name': 'Insulin', 'budgeted': 50, 'min_observed': 120, 'months_observed': 6}])
    check('s159 F4 a verdict names version 3, and Insulin is protected in it',
          v and v[0]['protected'] is True and v[0]['protected_rule_version'] == '3')

    # The mutation: version 2's substring matching put back must fail F2.
    check('s159 F2 mutation caught: substring matching protects "ER" by "water" and "Hospitality" by "hospital"',
          old('ER') and old('Hospitality') and not p('Hospitality'))
    check('s159 F2 "health" counts only as the whole name: "Health" is protected, "Health Club" (a gym) is not',
          p('Health') and p('health') and not p('Health Club') and p('Mental Health') and p('Health Insurance'))
