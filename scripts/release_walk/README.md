# Release walk

Press every control on every page of a throwaway Groundwork, enter data in its forms, and record what breaks. Used
for the 2.0 release walk (`gw 2.0/RELEASE_WALK.md`). Nothing here touches a real database: everything runs against
`dev_server.py`, which keeps its own temp database and, since 2026-11-08, its own vault entries.

Start a dev server on its own port (one per run that changes data):

    set GW_DEV_PORT=8793 && python dev_server.py

Then, from this folder:

| What | Command |
|---|---|
| Press everything, a fresh sample household per page | `node crawl.mjs http://127.0.0.1:8793 out_sample` |
| Press everything on an empty install | `node crawl.mjs http://127.0.0.1:8794 out_empty --empty` |
| Enter data in every form, one household throughout | `node crawl.mjs http://127.0.0.1:8794 out_fill --fill --once` |
| Press everything again on that same household | `node crawl.mjs http://127.0.0.1:8794 out_dirty --empty` |
| Only some pages | `node crawl.mjs <url> <out> byb,debt,settings` |
| What went wrong, grouped | `python triage.py out_sample/crawl.json out_empty/crawl.json` |
| Data that must survive a reload | `node scenarios.mjs <url> out_scen scenarios_data.mjs` |
| Before You Buy at three costs, with and without a plan | `node scenarios.mjs <url> out_byb scenarios_byb.mjs` |
| One smoke section alone | `python one_section.py s294_release_walk` |
| The math audit: raw records and every shown figure | `set GW_VIDEO_APP=<url> && node math_collect.mjs <url> math.json` |
| ... recomputed independently and compared | `python math_check.py math.json` |

The crawler blocks anything that would open a bank, airline or hotel window, uninstall, clear the sample, restore a
backup, delete a file from Downloads or check for updates; answers Groundwork's own confirm dialogs with Cancel; stubs
`print`, `alert`, `confirm`, `prompt` and `window.open`; refuses browser downloads; and points exports at a temp folder.
`CRAWL_PORT` picks its Chrome port (two crawls at once need two), `CRAWL_MAX` / `CRAWL_MS` cap clicks and time per page.

A 4xx in the triage is often the server's right answer to an empty form ("a name, please"): read the body before
calling it a bug.
