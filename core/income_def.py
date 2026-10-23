"""
Groundwork - what counts as income (gw 2.0/INCOME_CHANGE_SCENARIOS.md section 4, item 71 amendment D1)
====================================================================================================
One definition, used by every reader: a deposit counts as income when its category is

  - income-type, or
  - a child (at any depth) of the category named Income, or
  - named like one of the budget's income lines ("Alex's Income", "Sam's income").

Before this, readers matched the name "Income" exactly, so pay filed under a category named for the person was
invisible to the income figure while other pages, matching any name containing "income", counted it.
app.js `_isIncomeCategory` mirrors this rule.
"""


def income_category_ids(session):
    from core.database import BudgetItem, Category
    cats = {c.id: c for c in session.query(Category).all()}
    lines = {(b.name or '').strip().lower() for b in session.query(BudgetItem).filter_by(type='income').all()
             if (b.name or '').strip()}
    root = {cid for cid, c in cats.items() if (c.name or '').strip().lower() == 'income'}

    def under_income(c):
        seen = set()
        while c is not None and c.id not in seen:
            if c.id in root:
                return True
            seen.add(c.id)
            c = cats.get(c.parent_id)
        return False

    return {cid for cid, c in cats.items()
            if (c.type or '') == 'income' or under_income(c) or (c.name or '').strip().lower() in lines}
