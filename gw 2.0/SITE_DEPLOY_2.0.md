# Publishing the 2.0 website

groundworkfinance.app still serves the 1.1 site (checked 2026-11-08: the home page says Version 1.1; `/whats-new`,
`/demo-bank/` and `/demo-bill/` are 404). Everything for 2.0 is on `master`. Publishing is Rob's.

## What to upload

From `Website/` in the repo (a ready copy is built at `installer_output/site_deploy_2.0/`, which git does not track):

| File | Why |
|---|---|
| `website.py` | every page, the demo bank and biller, the help articles |
| `sample_lines.py` | **new** - the demo bank's downloads are built from it; the site fails to start without it |
| `changelog.json` | the 2.0 entry |
| `version.json` | the in-app update notice |
| `static/` (all of it) | the videos (`static/video/`, now with `start.*` and `debt.*`), the screenshots, the icon |

**Do not upload `subscribers.db`** - the server's copy is the live mailing list. Leave `sitemap.xml` as it is: the
site serves its own sitemap from `website.py`.

Then restart the site's Python service so it loads the new `website.py`.

## Release-day lines (unchanged, RELEASE_2_0.md)

- The 2.0 installers are what `/dl/` serves.
- `V11_FILE` / `V11_SHA256` in `website.py`: the 1.1.1 installer uploaded under its own name, and its SHA-256 filled
  in (the line stays hidden until it is - a checksum is never invented).
- `version.json`'s `latest` is the build being shipped (s206 checks it equals `GW_VERSION`).

## Check after publishing

- `/` - Version 2.0; the tours: Start here (Getting started, Debt Payoff), Go deeper (Ask, Health, Reports, Privacy).
- `/whats-new`, `/health`, `/download`.
- `/knowledge-base#get-accounts`, `#bills-biller`, `#voice`, `#first-run`, `#backup`.
- `/demo-bank/` - sign in with any name and password, the code page, accounts, a download.
- `/demo-bill/` - the bill and a Pay now that pays nothing.

## After it is live

Tell Claude: the Get my accounts tour (`scripts/site_video/fetch.json`) can then be filmed against the live demo bank,
with screenshots for its help article, and goes up with one more small upload (`website.py` and `static/video/fetch.*`).
