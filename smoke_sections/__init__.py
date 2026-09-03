"""Smoke-test sections, discovered and run by smoke_test.py.

One file per section. Each defines run(ctx); ctx carries check, BASE, TMP,
the test client c, headers H/HJ, the db_session factory dbs, and the
server/app.js/index.html sources. Files run in sorted filename order, so
the numeric prefix is the ordering knob.

Adding a section is adding a file. That is the point: the old shared
append anchor in main() made every forward-merge between lts/1.x and
master collide.
"""
