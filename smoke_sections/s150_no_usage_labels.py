"""No label about the person from how they use the app (gw 2.0/USAGE_SIGNALS.md, item 39; Rob 2026-10-05:
"remove rule on the dead label").

app.js labelled the user "engaged", "occasional" or "passive" from how many transactions they had in three months.
Nothing read it, and a sparse record can mean many things - "passive" is not one Groundwork can see (Willingness
Layer ruling, 2026-09-27: the label was set aside as its own question). It is removed, and this keeps it removed.
"""
import re


def run(ctx):
    check, app = ctx.check, ctx.app_src
    check('s150 item 39 the engaged / occasional / passive label is gone from app.js',
          'engagementLevel' not in app and not re.search(r"'engaged'\s*:|\?\s*'engaged'", app)
          and "'occasional'" not in app)
    check('s150 item 39 the behaviour profile no longer carries any engagement figure',
          'engagementLevel' not in app.split('function _calcBehavioralProfile', 1)[-1][:4000])
