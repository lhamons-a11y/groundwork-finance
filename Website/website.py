"""
Groundwork Finance — Website Backend
Flask app handling:
  - Homepage, download, knowledge base, about pages
  - Email signup with double opt-in
  - Admin panel for sending newsletters
  - SendGrid integration
"""

import os
import json
import secrets
import hashlib
import sqlite3
from html import escape as h
from datetime import datetime, timedelta
from pathlib import Path
from flask import (Flask, render_template_string, request, jsonify,
                   redirect, url_for, session, abort)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
ADMIN_PASSWORD   = os.environ.get('ADMIN_PASSWORD', 'changeme')
FROM_EMAIL       = 'hello@groundworkfinance.app'
FROM_NAME        = 'Groundwork'
SITE_URL         = 'https://groundworkfinance.app'
DOWNLOAD_URL     = 'https://groundworkfinance.app/static/download/Groundwork_Setup.exe'

DB_PATH = Path(os.environ.get('GW_SITE_DATA', '/var/www/groundwork')) / 'subscribers.db'

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS subscribers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT,
            token       TEXT,
            confirmed   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TEXT
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS emails_sent (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject     TEXT,
            body        TEXT,
            sent_count  INTEGER,
            sent_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # Aggregate analytics — no IPs, no cookies, no user agents, no PII.
        # One counter row per (path, day) and per (platform, day).
        db.execute('''CREATE TABLE IF NOT EXISTS page_views (
            path   TEXT NOT NULL,
            day    TEXT NOT NULL,
            count  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (path, day)
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS downloads (
            platform TEXT NOT NULL,
            day      TEXT NOT NULL,
            count    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (platform, day)
        )''')
        db.commit()

init_db()

# ── Analytics (aggregate counters only) ─────────────────────────────────────────
# Paths we never count as page views: static assets, the admin area, the
# download-counter redirect, and any URL carrying a per-user token.
_SKIP_VIEW_PREFIXES = ('/static', '/admin', '/dl', '/confirm', '/unsubscribe',
                       '/favicon', '/robots', '/sitemap')
_BOT_MARKERS = ('bot', 'crawl', 'spider', 'slurp', 'bingpreview', 'facebookexternalhit',
                'headlesschrome', 'python-requests', 'curl', 'wget')

def _today():
    return datetime.utcnow().strftime('%Y-%m-%d')

def _bump(table, key_col, key_val):
    """Increment an aggregate counter. Never raises — analytics must not
    break a page render or a download."""
    try:
        with get_db() as db:
            db.execute(
                f'INSERT INTO {table} ({key_col}, day, count) VALUES (?, ?, 1) '
                f'ON CONFLICT({key_col}, day) DO UPDATE SET count = count + 1',
                (key_val, _today()))
            db.commit()
    except Exception:
        pass

@app.after_request
def _count_page_view(resp):
    try:
        p = request.path
        if (request.method == 'GET'
                and resp.status_code == 200
                and (resp.content_type or '').startswith('text/html')
                and not p.startswith(_SKIP_VIEW_PREFIXES)):
            ua = (request.headers.get('User-Agent') or '').lower()
            if not any(m in ua for m in _BOT_MARKERS):
                _bump('page_views', 'path', p)
    except Exception:
        pass
    return resp

# ── SendGrid ──────────────────────────────────────────────────────────────────
def send_email(to_email, to_name, subject, html_body):
    if not SENDGRID_API_KEY:
        print(f"[EMAIL] Would send to {to_email}: {subject}")
        return True
    try:
        import urllib.request, json
        data = json.dumps({
            'personalizations': [{'to': [{'email': to_email, 'name': to_name}]}],
            'from': {'email': FROM_EMAIL, 'name': FROM_NAME},
            'subject': subject,
            'content': [{'type': 'text/html', 'value': html_body}],
        }).encode()
        req = urllib.request.Request(
            'https://api.sendgrid.com/v3/mail/send',
            data=data,
            headers={
                'Authorization': f'Bearer {SENDGRID_API_KEY}',
                'Content-Type':  'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req) as r:
            return r.status in (200, 202)
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False

def send_confirmation_email(email, name, token):
    confirm_url = f"{SITE_URL}/confirm/{token}"
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;padding:40px 20px">
      <h2 style="color:#1a1a2e;font-size:24px">Confirm your email</h2>
      <p style="color:#555;line-height:1.6">
        Hi {h(name) if name else 'there'}, thanks for signing up for Groundwork updates.
        Click the button below to confirm your email address.
      </p>
      <a href="{confirm_url}"
         style="display:inline-block;margin:24px 0;padding:14px 28px;
                background:#2d6a4f;color:#fff;text-decoration:none;
                border-radius:6px;font-weight:600">
        Confirm my email →
      </a>
      <p style="color:#999;font-size:12px">
        If you didn't sign up for Groundwork, just ignore this email.
      </p>
    </div>"""
    return send_email(email, name or '', 'Confirm your Groundwork signup', html)

# ── CSS / Design ──────────────────────────────────────────────────────────────
SITE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --ink:    #0f1b2d;
  --ink-2:  #16263d;
  --pine:   #1f7a5c;
  --pine-d: #17604a;
  --mint:   #3ddc97;
  --gold:   #f2c14e;
  --ember:  #e4572e;
  --paper:  #fbfaf6;
  --mist:   #f1f0ea;
  --steel:  #e3e1d8;
  --slate:  #4a5568;
  --muted:  #6b7280;
  --r:      12px;
  --shadow: 0 1px 2px rgba(15,27,45,.06), 0 8px 24px rgba(15,27,45,.06);
  --shadow-lg: 0 2px 4px rgba(15,27,45,.06), 0 24px 48px rgba(15,27,45,.12);
}
html { scroll-behavior: smooth; }
body { font-family: 'Inter', system-ui, sans-serif; background: var(--paper); color: var(--ink); line-height: 1.65;
       -webkit-font-smoothing: antialiased; }
h1, h2, h3, .display { font-family: 'Fraunces', Georgia, serif; letter-spacing: -.02em; }
a { color: var(--pine); text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 1160px; margin: 0 auto; padding: 0 24px; }
.narrow { max-width: 760px; margin: 0 auto; padding: 0 24px; }
.btn {
  display: inline-flex; align-items: center; gap: 8px; padding: 14px 26px; border-radius: 999px;
  font-weight: 600; font-size: 15px; cursor: pointer; border: none; font-family: inherit;
  transition: transform .15s, box-shadow .15s, background .15s;
}
.btn:hover { text-decoration: none; transform: translateY(-1px); }
.btn-primary { background: var(--pine); color: #fff; box-shadow: 0 6px 18px rgba(31,122,92,.28); }
.btn-primary:hover { background: var(--pine-d); }
.btn-light { background: #fff; color: var(--ink); box-shadow: var(--shadow); }
.btn-ghost { background: transparent; color: var(--pine); border: 1.5px solid var(--pine); }
.btn-ghost-light { background: rgba(255,255,255,.08); color: #fff; border: 1.5px solid rgba(255,255,255,.28); }
.btn-gold { background: var(--gold); color: var(--ink); }

/* Announcement bar */
.beta-bar { background: linear-gradient(90deg, #12324a, #1f7a5c); color: #fff; padding: 10px 24px;
            text-align: center; font-size: 14px; }
.beta-bar a { color: var(--gold); font-weight: 600; }

/* Nav */
.site-nav { background: rgba(251,250,246,.86); backdrop-filter: saturate(160%) blur(12px);
            -webkit-backdrop-filter: saturate(160%) blur(12px); border-bottom: 1px solid var(--steel);
            position: sticky; top: 0; z-index: 100; padding: 0 24px; }
.nav-inner { max-width: 1160px; margin: 0 auto; display: flex; align-items: center;
             justify-content: space-between; height: 68px; gap: 16px; }
.nav-logo { font-family: 'Fraunces', Georgia, serif; font-style: italic; color: var(--ink); font-size: 24px;
            font-weight: 700; letter-spacing: -.5px; display: flex; align-items: center; gap: 10px; }
.nav-logo:hover { text-decoration: none; }
.nav-logo em { color: var(--pine); font-style: italic; }
.nav-mark { width: 30px; height: 30px; border-radius: 8px; background: var(--ink); display: inline-flex;
            align-items: flex-end; justify-content: center; gap: 3px; padding: 6px; }
.nav-mark i { display: block; width: 4px; border-radius: 2px; background: var(--mint); }
.nav-links { display: flex; gap: 28px; align-items: center; }
.nav-links a { color: var(--slate); font-size: 14.5px; font-weight: 500; }
.nav-links a:hover { color: var(--ink); text-decoration: none; }
.nav-links a.nav-new { color: var(--pine); font-weight: 600; }
.nav-cta { background: var(--ink); color: #fff !important; padding: 9px 18px; border-radius: 999px; font-weight: 600 !important; }
.nav-cta:hover { background: var(--ink-2); }

/* Hero */
.hero { position: relative; overflow: hidden; color: #fff; padding: 96px 24px 88px;
        background: radial-gradient(1200px 600px at 85% -10%, rgba(61,220,151,.22), transparent 60%),
                    radial-gradient(900px 500px at -10% 110%, rgba(242,193,78,.16), transparent 60%),
                    linear-gradient(160deg, #0f1b2d 0%, #12324a 55%, #134b44 100%); }
.hero-inner { max-width: 1160px; margin: 0 auto; display: grid; grid-template-columns: 1.05fr .95fr;
              gap: 56px; align-items: center; }
.hero-center { text-align: center; max-width: 820px; margin: 0 auto; }
.beta-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,.1);
              border: 1px solid rgba(255,255,255,.18); color: #fff; font-size: 13px; font-weight: 600;
              padding: 6px 14px; border-radius: 999px; margin-bottom: 26px; }
.beta-badge b { width: 8px; height: 8px; border-radius: 50%; background: var(--mint); display: inline-block; }
.hero h1 { font-size: clamp(36px, 5.4vw, 64px); font-weight: 600; line-height: 1.06; margin-bottom: 22px; }
.hero h1 em { color: var(--mint); font-style: italic; }
.hero p.lead { font-size: 19px; color: rgba(255,255,255,.82); max-width: 560px; margin-bottom: 34px; }
.hero-center p.lead { margin-left: auto; margin-right: auto; }
.hero-btns { display: flex; gap: 14px; flex-wrap: wrap; }
.hero-center .hero-btns { justify-content: center; }
.hero-note { margin-top: 18px; font-size: 13px; color: rgba(255,255,255,.6); }

/* Hero app window (an illustration with sample figures) */
.appwin { background: #f7f6f1; border-radius: 16px; box-shadow: 0 40px 80px rgba(0,0,0,.35);
          overflow: hidden; transform: perspective(1400px) rotateY(-6deg) rotateX(3deg); color: var(--ink); }
.appwin-bar { background: #e9e7df; height: 34px; display: flex; align-items: center; gap: 7px; padding: 0 14px; }
.appwin-bar i { width: 11px; height: 11px; border-radius: 50%; display: block; }
.appwin-body { display: grid; grid-template-columns: 120px 1fr; min-height: 320px; }
.appwin-side { background: var(--ink); padding: 16px 12px; display: flex; flex-direction: column; gap: 9px; }
.appwin-side span { height: 8px; border-radius: 4px; background: rgba(255,255,255,.14); }
.appwin-side span.on { background: var(--mint); width: 70%; }
.appwin-main { padding: 18px; display: grid; gap: 12px; }
.tile { background: #fff; border: 1px solid var(--steel); border-radius: 10px; padding: 12px 14px; }
.tile-l { font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.tile-n { font-family: 'DM Mono', monospace; font-size: 20px; font-weight: 600; margin-top: 2px; }
.tile-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.tile-bars { display: flex; align-items: flex-end; gap: 5px; height: 54px; margin-top: 8px; }
.tile-bars i { flex: 1; border-radius: 3px 3px 0 0; background: var(--pine); opacity: .8; display: block; }
.tile-bars i.hi { background: var(--gold); opacity: 1; }
.tile-why { font-size: 11.5px; color: var(--slate); margin-top: 6px; }
.tile-why b { color: var(--pine); }
.sample-tag { text-align: right; font-size: 11px; color: rgba(255,255,255,.5); margin-top: 10px; }

/* Sections */
section { scroll-margin-top: 80px; }
.band { padding: 96px 24px; }
.band-mist { background: var(--mist); }
.band-ink { background: var(--ink); color: #fff; }
.section-label { display: inline-block; font-size: 12.5px; font-weight: 700; letter-spacing: .12em;
                 text-transform: uppercase; color: var(--pine); margin-bottom: 14px; }
.band-ink .section-label { color: var(--mint); }
.section-title { font-size: clamp(28px, 4vw, 46px); font-weight: 600; line-height: 1.12; margin-bottom: 16px; }
.section-sub { font-size: 18px; color: var(--slate); max-width: 640px; }
.band-ink .section-sub { color: rgba(255,255,255,.75); }
.center { text-align: center; }
.center .section-sub { margin: 0 auto; }

/* Pillars */
.pillars { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 52px; }
.pillar { background: #fff; border: 1px solid var(--steel); border-radius: 18px; padding: 28px 24px;
          box-shadow: var(--shadow); }
.pillar h3 { font-size: 21px; font-weight: 600; margin: 16px 0 8px; line-height: 1.25; }
.pillar p { font-size: 15px; color: var(--slate); }
.chip { width: 46px; height: 46px; border-radius: 12px; display: inline-flex; align-items: center;
        justify-content: center; }
.chip svg { width: 24px; height: 24px; }
.chip-pine { background: #e3f3ec; color: var(--pine); }
.chip-gold { background: #fdf3d8; color: #9a6b00; }
.chip-ember { background: #fde7df; color: #b33a14; }
.chip-ink { background: #e6ebf3; color: var(--ink); }

/* Feature grid */
.features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
                 gap: 18px; margin-top: 52px; }
.feature-card { background: #fff; border: 1px solid var(--steel); border-radius: 16px; padding: 26px;
                transition: box-shadow .2s, transform .2s; }
.feature-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.feature-card h3 { font-family: 'Inter', sans-serif; letter-spacing: -.01em; font-size: 17px;
                   font-weight: 700; margin: 14px 0 6px; }
.feature-card p { font-size: 15px; color: var(--slate); line-height: 1.65; }

/* Split rows */
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 64px; align-items: center; }
.split p { color: var(--slate); font-size: 17px; margin-bottom: 14px; }
.band-ink .split p { color: rgba(255,255,255,.78); }
.checklist { list-style: none; margin-top: 18px; display: grid; gap: 12px; }
.checklist li { padding-left: 32px; position: relative; font-size: 16px; color: var(--slate); }
.band-ink .checklist li { color: rgba(255,255,255,.82); }
.checklist li::before { content: ''; position: absolute; left: 0; top: 4px; width: 20px; height: 20px;
                        border-radius: 50%; background: var(--pine) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12l5 5L20 7'/%3E%3C/svg%3E") center/12px no-repeat; }
.panel { background: #fff; border: 1px solid var(--steel); border-radius: 20px; padding: 30px; box-shadow: var(--shadow-lg); }
.band-ink .panel { background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.12); box-shadow: none; }
.panel-row { display: flex; justify-content: space-between; gap: 16px; padding: 12px 0; border-bottom: 1px solid var(--steel); font-size: 15px; }
.band-ink .panel-row { border-color: rgba(255,255,255,.1); }
.panel-row:last-child { border-bottom: none; }
.panel-row b { font-weight: 600; }
.panel-row span { color: var(--slate); text-align: right; }
.band-ink .panel-row span { color: rgba(255,255,255,.7); }

/* Coming in 2.0 */
.next-hero { padding: 88px 24px 72px; }
.next-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr)); gap: 20px; margin-top: 48px; }
.next-card { background: #fff; border: 1px solid var(--steel); border-radius: 18px; padding: 28px; box-shadow: var(--shadow); }
.next-card h3 { font-size: 22px; font-weight: 600; margin: 14px 0 8px; line-height: 1.25; }
.next-card p { color: var(--slate); font-size: 15.5px; }
.next-card.design { background: var(--mist); border-style: dashed; box-shadow: none; }
.tag { display: inline-block; font-size: 11.5px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
       padding: 3px 10px; border-radius: 999px; background: #e3f3ec; color: var(--pine); margin-left: 8px; vertical-align: middle; }
.tag-design { background: #fdf3d8; color: #8a5d00; }
.teaser-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: 44px; }
.teaser { background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12); border-radius: 16px; padding: 24px; }
.teaser h3 { font-family: 'Inter', sans-serif; letter-spacing: -.01em; font-size: 17px; font-weight: 700; margin-bottom: 6px; color: #fff; }
.teaser p { font-size: 14.5px; color: rgba(255,255,255,.72); }

/* The horizon phrase is one line to the eye, always (Rob 2026-10-12) */
.fi { white-space: nowrap; }
.fi-head { font-size: clamp(13px, 4.6vw, 46px); }
@media (max-width: 360px) { .fi { font-size: .8em; letter-spacing: -.01em; } .fi-head .fi, .statement-line .fi { font-size: 1em; } }

/* The closing statement */
.statement { padding: 104px 24px; color: #fff; background:
  radial-gradient(700px 360px at 50% 0%, rgba(242,193,78,.18), transparent 70%),
  linear-gradient(160deg, #0f1b2d, #12324a); }
.statement-line { font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 600;
  font-size: clamp(14px, 4.8vw, 52px); line-height: 1.2; letter-spacing: -.02em; }
.statement-line .nobr { white-space: nowrap; }
.statement-sub { margin-top: 18px; font-size: 18px; color: rgba(255,255,255,.75); }

/* Signup */
.signup-section { padding: 88px 24px; text-align: center; color: #fff;
                  background: radial-gradient(800px 400px at 50% 0%, rgba(61,220,151,.22), transparent 70%), var(--pine-d); }
.signup-section h2 { font-size: clamp(28px, 4vw, 42px); font-weight: 600; margin-bottom: 12px; }
.signup-section p { color: rgba(255,255,255,.85); margin-bottom: 30px; font-size: 17px; }
.signup-form { display: flex; gap: 10px; max-width: 540px; margin: 0 auto; flex-wrap: wrap; justify-content: center; }
.signup-form input { flex: 1; min-width: 180px; padding: 14px 18px; border-radius: 999px; border: none;
                     font-size: 15px; font-family: inherit; }
.signup-form .btn { background: var(--gold); color: var(--ink); }
.signup-msg { margin-top: 16px; font-size: 14px; min-height: 20px; }

/* Footer */
footer { background: var(--ink); color: rgba(255,255,255,.62); padding: 56px 24px 40px; font-size: 14px; }
footer a { color: rgba(255,255,255,.78); }
.foot-grid { max-width: 1160px; margin: 0 auto; display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr; gap: 32px; }
.foot-grid h4 { color: #fff; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 12px; font-family: 'Inter', sans-serif; }
.foot-grid ul { list-style: none; display: grid; gap: 8px; }
.foot-brand { font-family: 'Fraunces', Georgia, serif; font-style: italic; color: #fff; font-size: 22px; font-weight: 700; margin-bottom: 8px; }
.foot-base { max-width: 1160px; margin: 36px auto 0; padding-top: 22px; border-top: 1px solid rgba(255,255,255,.1);
             display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; font-size: 13px; }

/* Page heads */
.page-head { padding: 80px 24px 56px; color: #fff; text-align: center;
             background: radial-gradient(900px 400px at 80% -20%, rgba(61,220,151,.2), transparent 60%),
                         linear-gradient(160deg, #0f1b2d, #12324a); }
.page-head h1 { font-size: clamp(32px, 4.6vw, 54px); font-weight: 600; margin-bottom: 12px; }
.page-head p { color: rgba(255,255,255,.78); font-size: 18px; max-width: 640px; margin: 0 auto; }
.prose { padding: 64px 24px; }
.prose h2 { font-size: 28px; font-weight: 600; margin: 40px 0 14px; }
.prose h2:first-child { margin-top: 0; }
.prose p { color: var(--slate); font-size: 17px; line-height: 1.85; margin-bottom: 16px; }
.prose ul { color: var(--slate); font-size: 16.5px; line-height: 1.8; padding-left: 22px; margin-bottom: 16px; }
.prose li { margin-bottom: 6px; }
.callout { background: #e3f3ec; border-left: 4px solid var(--pine); padding: 16px 20px; border-radius: 0 12px 12px 0;
           margin: 20px 0; color: var(--ink); font-size: 15.5px; }

/* Download page */
.download-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
                 gap: 22px; padding: 48px 24px 24px; }
.download-card { background: #fff; border: 1px solid var(--steel); border-radius: 20px; padding: 30px;
                 box-shadow: var(--shadow); display: flex; flex-direction: column; }
.download-card:hover { box-shadow: var(--shadow-lg); }
.download-card .os-icon { font-size: 40px; margin-bottom: 12px; }
.download-card h3 { font-size: 24px; font-weight: 600; margin-bottom: 6px; }
.download-card p { color: var(--slate); font-size: 15px; margin-bottom: 20px; }
.download-card .btn { justify-content: center; }
.requirements { background: var(--mist); border-radius: 12px; padding: 16px; font-size: 13.5px;
                color: var(--slate); margin-top: 18px; text-align: left; line-height: 1.7; }

/* KB */
.kb-grid { display: grid; grid-template-columns: 250px 1fr; gap: 48px; padding: 56px 24px; max-width: 1160px; margin: 0 auto; }
.kb-grid > * { min-width: 0; }
.kb-article p, .kb-article li { overflow-wrap: anywhere; }
footer a { overflow-wrap: anywhere; }
.kb-nav { position: sticky; top: 92px; align-self: start; background: #fff; border: 1px solid var(--steel);
          border-radius: 16px; padding: 18px; }
.kb-nav h3 { font-family: 'Inter', sans-serif; letter-spacing: .1em; font-size: 12px; font-weight: 700;
             text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
.kb-nav a { display: block; padding: 7px 10px; border-radius: 8px; font-size: 14px; color: var(--ink); }
.kb-nav a:hover, .kb-nav a.active { background: var(--mist); text-decoration: none; }
.kb-content h1 { font-size: 34px; font-weight: 600; margin-bottom: 8px; }
.kb-content .kb-sub { color: var(--slate); margin-bottom: 40px; font-size: 17px; }
.kb-article { margin-bottom: 44px; padding-bottom: 44px; border-bottom: 1px solid var(--steel); }
.kb-article h2 { font-size: 24px; font-weight: 600; margin-bottom: 12px; }
.kb-article h3 { font-family: 'Inter', sans-serif; letter-spacing: -.01em; font-size: 16px; font-weight: 700; margin: 20px 0 8px; }
.kb-article h4 { font-size: 14px; font-weight: 700; margin: 14px 0 6px; }
.kb-article p { color: var(--slate); line-height: 1.8; margin-bottom: 12px; }
.kb-article ul { color: var(--slate); padding-left: 20px; line-height: 1.9; }
.kb-tip { background: #e3f3ec; border-left: 3px solid var(--pine); padding: 12px 16px; color: var(--ink);
          border-radius: 0 10px 10px 0; font-size: 14.5px; margin: 16px 0; }

/* Admin */
.admin-wrap { max-width: 700px; margin: 60px auto; padding: 0 24px; }
.admin-card { background: #fff; border: 1px solid var(--steel); border-radius: 12px; padding: 32px; }
.field { margin-bottom: 20px; }
.field label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.field input, .field textarea { width: 100%; padding: 10px 14px; border: 1px solid var(--steel);
  border-radius: 8px; font-size: 14px; font-family: inherit; }
.field textarea { min-height: 200px; resize: vertical; }
.stats-row { display: flex; gap: 20px; margin-bottom: 24px; }
.stat-pill { background: var(--mist); border-radius: 8px; padding: 16px 20px; flex: 1; }
.stat-pill .n { font-size: 28px; font-weight: 800; color: var(--pine); }
.stat-pill .l { font-size: 12px; color: var(--slate); }

/* Reveal on scroll */
.reveal { opacity: 0; transform: translateY(14px); transition: opacity .6s ease, transform .6s ease; }
.reveal.in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) { .reveal { opacity: 1; transform: none; transition: none; } .appwin { transform: none; } }

@media (max-width: 980px) {
  .hero-inner, .split { grid-template-columns: 1fr; gap: 40px; }
  .pillars { grid-template-columns: 1fr 1fr; }
  .teaser-grid { grid-template-columns: 1fr; }
  .foot-grid { grid-template-columns: 1fr 1fr; }
  .appwin { transform: none; }
}
@media (max-width: 380px) {
  .site-nav { padding: 0 14px; }
  .nav-logo { font-size: 20px; gap: 7px; }
  .nav-cta { padding: 8px 13px; font-size: 13.5px !important; }
}
@media (max-width: 720px) {
  .nav-links a:not(.nav-cta) { display: none; }
  .pillars { grid-template-columns: 1fr; }
  .kb-grid { grid-template-columns: 1fr; }
  .kb-nav { position: static; }
  .foot-grid { grid-template-columns: 1fr; }
  .band { padding: 72px 20px; }
  .appwin-body { grid-template-columns: 1fr; }
  .appwin-side { display: none; }
}
"""

# ── Icons (inline, so the site loads nothing extra) ──────────────────────────
_ICON_PATHS = {
    'chart':  '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    'book':   '<path d="M2 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2z"/><path d="M22 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z"/>',
    'heart':  '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/>',
    'shield': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    'wallet': '<rect x="2" y="6" width="20" height="14" rx="2"/><path d="M16 13h2"/><path d="M2 10h20"/>',
    'card':   '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><path d="M6 15h4"/>',
    'list':   '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
    'trend':  '<path d="M22 7l-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    'gift':   '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v9H5v-9"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5C11 3 12 8 12 8s1-5 4.5-5a2.5 2.5 0 0 1 0 5"/>',
    'plane':  '<path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
    'cart':   '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>',
    'file':   '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    'spark':  '<path d="M12 3l1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2z"/><path d="M19 17l.8 2.2L22 20l-2.2.8L19 23l-.8-2.2L16 20l2.2-.8z"/>',
    'lock':   '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    'import': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    'bank':   '<path d="M3 21h18"/><path d="M5 21V10"/><path d="M19 21V10"/><path d="M9 21V10"/><path d="M15 21V10"/><path d="M2 10l10-7 10 7"/>',
    'bill':   '<path d="M4 2v20l3-2 3 2 2-2 2 2 3-2 3 2V2l-3 2-3-2-2 2-2-2-3 2z"/><path d="M8 9h8"/><path d="M8 13h6"/>',
    'ask':    '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    'pay':    '<path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    'fork':   '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M6 9v1a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4V9"/><path d="M12 14v1"/>',
    'cal':    '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    'flame':  '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3.3.4 1.4 1.4 2.8 2.5 2.8z"/>',
    'micro':  '<path d="M9 2v6l-5 9a3 3 0 0 0 2.6 4.5h10.8A3 3 0 0 0 20 17l-5-9V2"/><path d="M8 2h8"/><path d="M7 15h10"/>',
    'cpu':    '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3"/><path d="M15 1v3"/><path d="M9 20v3"/><path d="M15 20v3"/><path d="M20 9h3"/><path d="M20 14h3"/><path d="M1 9h3"/><path d="M1 14h3"/>',
    'math':   '<path d="M4 4h16v16H4z"/><path d="M8 8h3"/><path d="M9.5 6.5v3"/><path d="M13 8h3"/><path d="M8 15l2 2"/><path d="M10 15l-2 2"/><path d="M13 15h3"/><path d="M13 17h3"/>',
    'eye':    '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    'pulse':  '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    'arrow':  '<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>',
}


def _icon(name):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + _ICON_PATHS[name] + '</svg>')


def _icons(html):
    """Swap each [[name]] in a page for its inline icon."""
    for name in _ICON_PATHS:
        html = html.replace('[[' + name + ']]', _icon(name))
    return html


SITE_VERSION = '1.1.1'   # the version offered for download; s205 holds it to the changelog's newest entry

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} — Groundwork</title>
  <meta name="description" content="{{ description }}">
  <meta name="theme-color" content="#0f1b2d">
  <link rel="canonical" href="{{ canonical }}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Groundwork">
  <meta property="og:title" content="{{ title }} — Groundwork">
  <meta property="og:description" content="{{ description }}">
  <meta property="og:url" content="{{ canonical }}">
  <meta property="og:image" content="https://groundworkfinance.app/static/groundwork_256.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{ title }} — Groundwork">
  <meta name="twitter:description" content="{{ description }}">
  <meta name="twitter:image" content="https://groundworkfinance.app/static/groundwork_256.png">
  {{ structured_data|default('')|safe }}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,600;1,9..144,700&family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>""" + SITE_CSS + """</style>
</head>
<body>

<div class="beta-bar">
  <strong>Groundwork """ + SITE_VERSION + """ is here</strong>: free for Windows, macOS and Linux.
  &nbsp;·&nbsp; <a href="/coming">See what's coming in 2.0 →</a>
</div>

<nav class="site-nav">
  <div class="nav-inner">
    <a href="/" class="nav-logo"><span class="nav-mark"><i style="height:7px"></i><i style="height:12px"></i><i style="height:17px"></i></span><span class="nav-word">Ground<em>work</em></span></a>
    <div class="nav-links">
      <a href="/features">Features</a>
      <a href="/coming" class="nav-new">Coming in 2.0</a>
      <a href="/knowledge-base">Help</a>
      <a href="/about">About</a>
      <a href="/privacy">Privacy</a>
      <a href="/download" class="nav-cta">Download free</a>
    </div>
  </div>
</nav>

{% block content %}{% endblock %}

<footer>
  <div class="foot-grid">
    <div>
      <div class="foot-brand">Groundwork</div>
      <p style="max-width:300px">Your whole financial picture, explained, with nothing to sell you, toward one horizon: <span class="fi">financial independence, for everyone</span>. Free, and it runs on your own computer.</p>
    </div>
    <div>
      <h4>Product</h4>
      <ul>
        <li><a href="/features">Features</a></li>
        <li><a href="/coming">Coming in 2.0</a></li>
        <li><a href="/download">Download</a></li>
        <li><a href="/changelog">Changelog</a></li>
      </ul>
    </div>
    <div>
      <h4>Help</h4>
      <ul>
        <li><a href="/knowledge-base">Knowledge base</a></li>
        <li><a href="/knowledge-base#install">Installing</a></li>
        <li><a href="/knowledge-base#report-bug">Reporting a problem</a></li>
        <li><a href="/signup">Email updates</a></li>
      </ul>
    </div>
    <div>
      <h4>Groundwork</h4>
      <ul>
        <li><a href="/about">About</a></li>
        <li><a href="/privacy">Privacy</a></li>
        <li><a href="/terms">Terms</a></li>
        <li><a href="mailto:hello@groundworkfinance.app">hello@groundworkfinance.app</a></li>
      </ul>
    </div>
  </div>
  <div class="foot-base">
    <span>© 2026 Groundwork · Free personal finance software</span>
    <span>No account · No subscription · No ads · Your data stays on your computer</span>
  </div>
</footer>

<script>
// Swap "Windows" in download CTAs for the visitor's actual OS, detected from
// the user agent. No-op on pages with no .os-download-label elements, and on
// mobile/unrecognized user agents the CTA just keeps its default text — the
// download page itself lists all three platforms, so this is a hint, not the
// only way to find the right download.
(function () {
  var els = document.querySelectorAll('.os-download-label');
  if (!els.length) return;
  var ua = navigator.userAgent;
  // iPhone/iPod/iPad first: a real iPhone's UA contains "like Mac OS X" and
  // would otherwise misdetect as macOS. Modern iPadOS Safari goes further and
  // fully spoofs a desktop Mac UA with no "iPad" substring at all — the only
  // way to catch that case is the touch-capable MacIntel platform check.
  var isAppleMobile = /iPhone|iPod|iPad/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var label = null;
  if (isAppleMobile) label = null;
  else if (/Mac OS X|Macintosh/.test(ua)) label = 'macOS';
  else if (/Linux/.test(ua) && !/Android/.test(ua)) label = 'Linux';
  else if (/Windows/.test(ua)) label = 'Windows';
  if (!label) return;
  els.forEach(function (el) { el.textContent = label; });
})();
// Sections fade in as they scroll into view; with reduced motion, or no
// IntersectionObserver, everything is simply shown.
(function () {
  var els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) { els.forEach(function (e) { e.classList.add('in'); }); return; }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
  }, { threshold: 0.12 });
  els.forEach(function (e) { io.observe(e); });
})();
</script>
</body>
</html>"""

# ── Pages ─────────────────────────────────────────────────────────────────────

_HOME_STRUCTURED_DATA = '<script type="application/ld+json">' + json.dumps({
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    'name': 'Groundwork',
    'applicationCategory': 'FinanceApplication',
    'operatingSystem': 'Windows, macOS, Linux',
    'description': 'A free personal finance app that tracks your whole financial picture, explains it, and has '
                   'nothing to sell you. No account, no subscription, no ads; your data stays on your computer.',
    'url': SITE_URL,
    'downloadUrl': SITE_URL + '/download',
    'softwareVersion': SITE_VERSION,
    'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'},
}) + '</script>'


@app.route('/')
def home():
    return render_template_string(BASE_TEMPLATE.replace(
        '{% block content %}{% endblock %}', HOME_CONTENT
    ), title='Your whole financial picture, explained',
       description='Groundwork is a free personal finance app that tracks your whole financial picture, explains it, '
                   'and has nothing to sell you. No account, no subscription, no ads. Your data stays on your computer.',
       canonical=SITE_URL + '/',
       structured_data=_HOME_STRUCTURED_DATA)

SIGNUP_SCRIPT = """
<script>
async function submitSignup() {
  const name  = document.getElementById('signup-name').value.trim();
  const email = document.getElementById('signup-email').value.trim();
  const msg   = document.getElementById('signup-msg');
  if (!email) { msg.textContent = 'Enter your email address.'; return; }
  msg.textContent = 'Signing you up…';
  try {
    const r = await fetch('/api/signup', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name, email}),
    });
    const d = await r.json();
    msg.textContent = d.message;
    if (d.ok) {
      document.getElementById('signup-name').value = '';
      document.getElementById('signup-email').value = '';
    }
  } catch(e) {
    msg.textContent = 'Something went wrong. Try again.';
  }
}
</script>
"""

SIGNUP_BAND = """
<section class="signup-section">
  <div class="container">
    <h2>Be first to hear about 2.0</h2>
    <p>One email when something worth knowing ships. No spam, and every email has a one-click unsubscribe.</p>
    <div class="signup-form">
      <input type="text" id="signup-name" placeholder="Your name" style="max-width:170px" aria-label="Your name">
      <input type="email" id="signup-email" placeholder="Your email address" aria-label="Your email address">
      <button class="btn" onclick="submitSignup()">Notify me →</button>
    </div>
    <div class="signup-msg" id="signup-msg"></div>
  </div>
</section>
""" + SIGNUP_SCRIPT

HOME_CONTENT = _icons("""
<section class="hero">
  <div class="hero-inner">
    <div>
      <div class="beta-badge"><b></b> Version """ + SITE_VERSION + """ · Free for Windows, macOS and Linux</div>
      <h1>Your whole financial picture, <em>explained.</em> And nothing to sell you.</h1>
      <p class="lead">Groundwork is a free personal finance app that tracks your money, explains what it shows you,
        and never tries to sell you a loan, a card or a subscription. It runs on your own computer, and it's built for
        everyone: whether you're paying down $12,000 or deciding where your first $10,000 goes.</p>
      <div class="hero-btns">
        <a href="/download" class="btn btn-primary" style="font-size:16px;padding:15px 30px">
          Download free for <span class="os-download-label">Windows</span>
        </a>
        <a href="/coming" class="btn btn-ghost-light">See what's coming in 2.0 →</a>
      </div>
      <div class="hero-note">No account. No subscription. No ads. Your data never leaves your computer.</div>
    </div>
    <div>
      <div class="appwin" role="img" aria-label="An illustration of the Groundwork dashboard, with sample figures">
        <div class="appwin-bar"><i style="background:#e4572e"></i><i style="background:#f2c14e"></i><i style="background:#3ddc97"></i></div>
        <div class="appwin-body">
          <div class="appwin-side"><span class="on"></span><span></span><span></span><span></span><span></span><span></span></div>
          <div class="appwin-main">
            <div class="tile-row">
              <div class="tile"><div class="tile-l">Income this month</div><div class="tile-n">$5,200</div></div>
              <div class="tile"><div class="tile-l">Spent so far</div><div class="tile-n" style="color:#b33a14">$3,916</div></div>
            </div>
            <div class="tile">
              <div class="tile-l">Left this month</div>
              <div class="tile-n" style="color:#1f7a5c">$1,284</div>
              <div class="tile-why"><b>How:</b> $5,200 income − $3,916 spent. Nothing estimated.</div>
              <div class="tile-bars"><i style="height:52%"></i><i style="height:70%"></i><i style="height:44%"></i><i style="height:82%"></i><i style="height:60%"></i><i class="hi" style="height:96%"></i></div>
            </div>
            <div class="tile-row">
              <div class="tile"><div class="tile-l">Net worth</div><div class="tile-n">$18,450</div></div>
              <div class="tile"><div class="tile-l">Debt-free</div><div class="tile-n" style="font-size:16px">Mar 2028</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="sample-tag">Illustration · sample figures</div>
    </div>
  </div>
</section>

<section class="band band-mist" style="padding:72px 24px">
  <div class="container center reveal">
    <div class="section-label">Our horizon</div>
    <h2 class="section-title fi-head"><span class="fi">Financial independence, for everyone</span></h2>
    <p class="section-sub">That's what Groundwork is for. Not one budget or one payoff date, but the long road to
      the point where your money supports the life you choose. Every feature is a step toward it, and every step is
      yours to take.</p>
  </div>
</section>

<section class="band">
  <div class="container center reveal">
    <div class="section-label">What Groundwork stands for</div>
    <h2 class="section-title">Four promises, kept in every screen</h2>
    <p class="section-sub">Groundwork is a full finance app, not a debt app with extras. Debt payoff is one tool in it:
      front and center if you're in debt, and never the definition of who you are.</p>
  </div>
  <div class="container pillars reveal">
    <div class="pillar">
      <span class="chip chip-pine">[[chart]]</span>
      <h3>It tracks everything</h3>
      <p>Budget, ledger, net worth, investments, debt and health care spending, built from your own bank files.</p>
    </div>
    <div class="pillar">
      <span class="chip chip-gold">[[book]]</span>
      <h3>It explains what it shows</h3>
      <p>What a term means and how a number was worked out, so the next decision is easier to make on your own.</p>
    </div>
    <div class="pillar">
      <span class="chip chip-ember">[[heart]]</span>
      <h3>Health care is a cost, not a failure</h3>
      <p>Health care spending is tracked as its own category, and Groundwork doesn't suggest cutting it.</p>
    </div>
    <div class="pillar">
      <span class="chip chip-ink">[[shield]]</span>
      <h3>It has nothing to sell you</h3>
      <p>No loan, no card, no subscription, no ads, and no product behind the advice. The software is the product, not you.</p>
    </div>
  </div>
</section>

<section class="band band-mist">
  <div class="container reveal">
    <div class="section-label">In Groundwork today</div>
    <h2 class="section-title">Everything in one place, on your own computer</h2>
    <p class="section-sub">These all work in the version you can download right now.</p>
    <div class="features-grid">
      <div class="feature-card"><span class="chip chip-pine">[[import]]</span><h3>Import from your bank</h3>
        <p>Bring in the CSV, OFX, QFX or QIF file your bank already gives you. Groundwork sorts it into categories and skips duplicates: no retyping.</p></div>
      <div class="feature-card"><span class="chip chip-pine">[[wallet]]</span><h3>A budget that follows your spending</h3>
        <p>See each budget line next to what you've actually spent this month, from your imported transactions.</p></div>
      <div class="feature-card"><span class="chip chip-ember">[[card]]</span><h3>Debt payoff planner</h3>
        <p>Snowball or avalanche: Groundwork lays out the payoff order and shows your debt-free date.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[trend]]</span><h3>Net worth and investments</h3>
        <p>Everything you own minus everything you owe, tracked month by month, with your holdings at their prices.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[gift]]</span><h3>Gift and seasonal planning</h3>
        <p>Every person and occasion in one list, with savings funds for the big ones, so the holidays aren't a surprise.</p></div>
      <div class="feature-card"><span class="chip chip-ink">[[plane]]</span><h3>Trip planner</h3>
        <p>Price a trip from your own numbers: your car's mileage and gas prices if you drive, Google Flights if you fly.</p></div>
      <div class="feature-card"><span class="chip chip-ink">[[cart]]</span><h3>Before You Buy</h3>
        <p>See what a big purchase does to your budget and your debt-free date before you decide. No lecture, just the numbers.</p></div>
      <div class="feature-card"><span class="chip chip-pine">[[file]]</span><h3>Reports you can print</h3>
        <p>Monthly spending, budget against actual, debt progress, net worth over time and more, each with a Print button.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[spark]]</span><h3>Local AI, if you want it</h3>
        <p>Optional plain-English write-ups of your month, from an AI model that runs on your own computer. Nothing is sent anywhere.</p></div>
    </div>
    <div style="text-align:center;margin-top:44px"><a href="/features" class="btn btn-ghost">See every feature →</a></div>
  </div>
</section>

<section class="band band-ink">
  <div class="container split reveal">
    <div>
      <div class="section-label">Private by design</div>
      <h2 class="section-title" style="color:#fff">Your money stays on your computer</h2>
      <p>Groundwork is a desktop app. Your transactions, balances, budgets and debts live in one file on your own
        machine. There's no account to make and no server holding your finances.</p>
      <ul class="checklist">
        <li>No account and no login</li>
        <li>No telemetry, no analytics, no usage tracking in the app</li>
        <li>No cloud AI: the AI runs on your computer or not at all</li>
        <li>Uninstalling never deletes your data</li>
      </ul>
    </div>
    <div class="panel">
      <div style="font-weight:700;margin-bottom:6px">What does leave your computer, and why</div>
      <div style="font-size:14px;color:rgba(255,255,255,.65);margin-bottom:10px">None of these carries a balance, a transaction or an amount.</div>
      <div class="panel-row"><b>Update check</b><span>asks whether there's a new version, and sends nothing about you</span></div>
      <div class="panel-row"><b>Investment prices</b><span>ticker symbols, to Yahoo Finance</span></div>
      <div class="panel-row"><b>Utility and fuel prices</b><span>your state, to the U.S. Energy Information Administration</span></div>
      <div class="panel-row"><b>Trip distances</b><span>the places you type, to OpenStreetMap</span></div>
      <div style="margin-top:14px"><a href="/privacy" style="color:var(--mint)">Read the privacy policy →</a></div>
    </div>
  </div>
</section>

<section class="band">
  <div class="container center reveal">
    <div class="section-label">Coming in Groundwork 2.0</div>
    <h2 class="section-title">The biggest update we've ever built</h2>
    <p class="section-sub">Groundwork 2.0 is being built and tested right now. It does more of the work for you,
      explains more of what it finds, and still keeps every number on your computer.</p>
  </div>
  <div class="container reveal">
    <div class="teaser-grid" style="margin-top:44px">
      <div class="feature-card"><span class="chip chip-pine">[[bank]]</span><h3>Your statements, with one press</h3><p>When you ask, Groundwork opens your bank's site and brings your statements back for you to review.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[ask]]</span><h3>Ask why</h3><p>A number looks wrong? Groundwork checks your records, tells you what it found, and shows any fix before it happens.</p></div>
      <div class="feature-card"><span class="chip chip-ink">[[fork]]</span><h3>Possible futures</h3><p>Your next twelve months side by side, including the rough ones, each saying exactly what it assumes.</p></div>
      <div class="feature-card"><span class="chip chip-ember">[[bill]]</span><h3>Bills, read from the biller</h3><p>The amount and due date from the company's own site, next to your budget. Groundwork never presses Pay.</p></div>
      <div class="feature-card"><span class="chip chip-pine">[[pay]]</span><h3>Your pay, employer by employer</h3><p>If a paycheck stops or drops, Groundwork says so plainly, without mistaking overtime for a raise.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[cal]]</span><h3>A Sunday check-in</h3><p>A short look at the week behind you and the week ahead: a paycheck due, a bill coming up.</p></div>
    </div>
    <div style="text-align:center;margin-top:44px"><a href="/coming" class="btn btn-primary">See everything coming in 2.0 →</a></div>
  </div>
</section>

<section class="band band-mist">
  <div class="container split reveal">
    <div>
      <div class="section-label">Who it's for</div>
      <h2 class="section-title">For wherever you're starting from</h2>
      <p>Most finance apps are built for one kind of person. Groundwork is built for anyone who wants to understand
        their money: whether you're working out how to make rent and pay down a card, or deciding where your first
        $10,000 should go.</p>
      <p>It started as one family's tool for getting their finances under control. It's free, and it will stay free.</p>
      <a href="/about" class="btn btn-ghost" style="margin-top:6px">Our story →</a>
    </div>
    <div class="panel">
      <div class="panel-row"><b>Price</b><span>$0, always</span></div>
      <div class="panel-row"><b>Account needed</b><span>None</span></div>
      <div class="panel-row"><b>Where your data lives</b><span>On your computer</span></div>
      <div class="panel-row"><b>Ads, upsells, partner offers</b><span>None</span></div>
      <div class="panel-row"><b>Works on</b><span>Windows, macOS and Linux</span></div>
    </div>
  </div>
</section>

<section class="statement">
  <div class="container center reveal">
    <p class="statement-line"><span class="nobr">Financial independence for everyone,</span><br><span class="nobr">one understood decision at a time.</span></p>
    <p class="statement-sub">That's why Groundwork explains every number it shows you, and has nothing to sell you.</p>
    <a href="/download" class="btn btn-gold" style="margin-top:26px">Start with Groundwork, free</a>
  </div>
</section>
""") + SIGNUP_BAND

# ── Download counter ──────────────────────────────────────────────────────────
# The download buttons point here so each click is counted by platform, then
# redirected to the real file (still served straight from /static in prod).
_DL_MAP = {
    'windows':         '/static/download/Groundwork_Setup.exe',
    'windows-offline': '/static/download/Groundwork_Setup_Offline.exe',
    'macos':           '/static/download/Groundwork-macos.zip',
    'linux':           '/static/download/Groundwork-linux-x86_64.tar.gz',
}

@app.route('/dl/<platform>')
def download_file(platform):
    target = _DL_MAP.get(platform)
    if not target:
        abort(404)
    _bump('downloads', 'platform', platform)
    return redirect(target)

# ── Download page ─────────────────────────────────────────────────────────────
@app.route('/download')
def download():
    content = """
<section class="page-head">
  <div class="beta-badge"><b></b> Version """ + SITE_VERSION + """ · Now available</div>
  <h1>Download Groundwork</h1>
  <p>Free. No account. No subscription. Your data stays on your computer.</p>
</section>

<div class="container" style="padding-top:40px">
  <div class="callout" style="max-width:860px;margin:0 auto">
    <strong>Use a system that still gets security updates.</strong> Groundwork holds your financial data, and an
    up-to-date operating system is the first thing protecting it - so we suggest running it on one that is still
    supported. Groundwork doesn't refuse an older system: on an older computer that stays offline, that's perfectly fine.
  </div>
</div>
<div class="download-grid container">
  <div class="download-card">
    <div class="os-icon">🪟</div>
    <h3>Windows</h3>
    <p>Windows 11 suggested. Double-click the installer and you're done in about a minute.</p>
    <a href="/dl/windows" class="btn btn-primary">⬇ Download for Windows</a>
    <div class="requirements">
      <strong>Requirements:</strong><br>
      Windows 11 (64-bit) suggested; Windows 10 still works<br>
      Microsoft Edge WebView2 (usually already installed)<br>
      ~2.5GB disk space (includes the built-in local AI model)<br>
      4GB RAM (8GB+ for the optional local AI)
    </div>
    <div style="margin-top:12px;font-size:13px;color:var(--slate)">
      Every Windows installer includes the local AI model (about 2.2GB of the
      download), so there is nothing to download later. The
      <a href="/dl/windows-offline">offline installer</a> is the same file,
      kept under its own link.
    </div>
  </div>

  <div class="download-card">
    <div class="os-icon">🍎</div>
    <h3>macOS</h3>
    <p>Apple Silicon and Intel Macs. Unzip and drag Groundwork into Applications.</p>
    <a href="/dl/macos" class="btn btn-primary">⬇ Download for macOS</a>
    <div class="requirements">
      <strong>Requirements:</strong><br>
      macOS 12 Monterey or later (a version Apple still updates is suggested)<br>
      ~150MB disk space<br>
      4GB RAM<br>
      Local AI: coming to Apple Silicon Macs. Intel Macs run Groundwork fully, without local AI.
    </div>
  </div>

  <div class="download-card">
    <div class="os-icon">🐧</div>
    <h3>Linux</h3>
    <p>Prebuilt x86_64 binary — no Python or system packages required. Extract and run.</p>
    <a href="/dl/linux" class="btn btn-primary">⬇ Download for Linux</a>
    <div class="requirements">
      <strong>Requirements:</strong><br>
      Ubuntu 22.04+, Debian 12+, Fedora, or similar (x86_64), on a release that still gets security updates<br>
      ~150MB disk space<br>
      4GB RAM<br>
      Local AI: coming to Linux. Groundwork runs fully without it.<br>
      <a href="/knowledge-base#linux">Installing from source →</a>
    </div>
  </div>
</div>

<div class="container center" style="padding:40px 24px 80px">
  <h3 style="font-size:24px;margin-bottom:10px">Having trouble installing?</h3>
  <p style="color:var(--slate)">
    Check the <a href="/knowledge-base#install">installation guide</a> or
    email <a href="mailto:support@groundworkfinance.app">support@groundworkfinance.app</a>
  </p>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Download',
        description='Download Groundwork free for Windows, macOS, or Linux. No account, no subscription — your financial data stays on your computer.',
        canonical=SITE_URL + '/download'
    )

# ── Knowledge Base ────────────────────────────────────────────────────────────
@app.route('/knowledge-base')
def knowledge_base():
    content = """
<section class="page-head">
  <h1>Knowledge Base</h1>
  <p>Everything you need to get started and get the most out of Groundwork</p>
</section>

<div class="kb-grid">
  <nav class="kb-nav">
    <h3>Getting Started</h3>
    <a href="#install">Installation</a>
    <a href="#first-run">First run & onboarding</a>
    <a href="#import">Importing transactions</a>
    <a href="#macos">macOS install</a>
    <a href="#linux">Linux install</a>
    <h3 style="margin-top:20px">Features</h3>
    <a href="#budget">Budget</a>
    <a href="#debt">Debt tracker</a>
    <a href="#ledger">Ledger</a>
    <a href="#networth">Net worth</a>
    <a href="#gifts">Gift budget</a>
    <a href="#investments">Investments</a>
    <a href="#reports">Reports</a>
    <a href="#byb">Before You Buy</a>
    <a href="#trip">Trip planner</a>
    <h3 style="margin-top:20px">Help</h3>
    <a href="#backup">Backups</a>
    <a href="#ai">AI features</a>
    <a href="#privacy">Privacy & data</a>
    <a href="#report-bug">Report a bug</a>
  </nav>

  <div class="kb-content">
    <h1>Help & Documentation</h1>
    <p class="kb-sub">This guide describes Groundwork """ + SITE_VERSION + """, the version offered for download. For what's on the way, see <a href="/coming">Coming in 2.0</a>.</p>

    <div class="kb-article" id="install">
      <h2>Installing Groundwork on Windows</h2>
      <p>Download the installer from the <a href="/download">Download page</a> and double-click <strong>Groundwork_Setup.exe</strong>.</p>
      <p>Windows may show a SmartScreen warning — "Windows protected your PC." This happens because Groundwork isn't yet code-signed. Click <strong>More info → Run anyway</strong>. The app is completely safe.</p>
      <h3>Microsoft Edge WebView2</h3>
      <p>Groundwork uses Microsoft Edge WebView2 to display its interface. On most Windows machines it's already installed. If it's not, the installer will prompt you to download it (it's free and takes about 30 seconds).</p>
      <div class="kb-tip">💡 If the app opens with a blank white screen, restart your computer and try again. This usually fixes it on first install.</div>
    </div>

    <div class="kb-article" id="first-run">
      <h2>First run & onboarding</h2>
      <p>When you open Groundwork for the first time, it walks you through a 6-step setup:</p>
      <ul>
        <li><strong>Step 1 — Income:</strong> Enter your take-home pay (after taxes). Monthly amount.</li>
        <li><strong>Step 2 — Expenses:</strong> Your regular monthly bills — rent, utilities, subscriptions.</li>
        <li><strong>Step 3 — Debt:</strong> Add your credit cards, loans, and leases with their balances and rates.</li>
        <li><strong>Step 4 — Strategy:</strong> Pick snowball (smallest balance first) or avalanche (highest rate first).</li>
        <li><strong>Step 5 — Net worth goal:</strong> Optional — set a target net worth to work toward.</li>
        <li><strong>Step 6 — Your plan:</strong> Groundwork shows your debt-free date and monthly plan.</li>
      </ul>
      <div class="kb-tip">💡 You can change everything after setup. Nothing is locked in.</div>
    </div>

    <div class="kb-article" id="import">
      <h2>Importing bank transactions</h2>
      <p>Groundwork imports transaction files from your bank. Most banks let you export these from your online account.</p>
      <h3>Supported formats</h3>
      <ul>
        <li><strong>CSV</strong> — comma-separated values, exported by almost every bank</li>
        <li><strong>OFX / QFX</strong> — Open Financial Exchange format, used by Quicken exports</li>
        <li><strong>QIF</strong> — Quicken Interchange Format (older format, still supported)</li>
      </ul>
      <h3>How to import</h3>
      <p>1. Log into your bank's website and find the transaction export/download option (usually under Account Activity or Statements).</p>
      <p>2. In Groundwork, click the <strong>Import</strong> button in the Ledger or top toolbar.</p>
      <p>3. Select your account, choose the file, and click Import.</p>
      <p>4. Groundwork automatically categorizes transactions and removes duplicates.</p>
      <div class="kb-tip">💡 Groundwork remembers the categories you choose and applies them to similar transactions in later imports.</div>
    </div>

    <div class="kb-article" id="linux">
      <h2>Installing on Linux</h2>
      <p>Fastest way: download the prebuilt binary from the <a href="/download">Download page</a> — no Python or system packages needed.</p>
      <pre style="background:var(--ink);color:#fff;padding:16px;border-radius:var(--r);font-size:13px;overflow-x:auto">tar -xzf Groundwork-linux-x86_64.tar.gz
cd Groundwork
./Groundwork</pre>
      <div class="kb-tip">💡 x86_64 only for now. If you're on a different architecture, or prefer to run from source, see below.</div>
      <h3>Running from source instead</h3>
      <p>Requires Python 3.11+ and a few system packages — the exact webkit2gtk package name depends on your distro version.</p>
      <h4>Ubuntu 22.04 / Debian 11</h4>
      <pre style="background:var(--ink);color:#fff;padding:16px;border-radius:var(--r);font-size:13px;overflow-x:auto">sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.0 python3-tk
pip3 install -r requirements.txt
python3 launch.py</pre>
      <h4>Ubuntu 23.04+ / Debian 12+</h4>
      <pre style="background:var(--ink);color:#fff;padding:16px;border-radius:var(--r);font-size:13px;overflow-x:auto">sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.1 python3-tk
pip3 install -r requirements.txt
python3 launch.py</pre>
      <h4>Fedora</h4>
      <pre style="background:var(--ink);color:#fff;padding:16px;border-radius:var(--r);font-size:13px;overflow-x:auto">sudo dnf install python3-gobject webkit2gtk4.0 python3-tkinter
pip3 install -r requirements.txt
python3 launch.py</pre>
    </div>

    <div class="kb-article" id="macos">
      <h2>Installing on macOS</h2>
      <p>Download the .zip from the <a href="/download">Download page</a>, unzip it, and drag <strong>Groundwork.app</strong> into your Applications folder.</p>
      <p>macOS may show a Gatekeeper warning — "Groundwork can't be opened because it is from an unidentified developer." This happens because the app isn't yet code-signed. Right-click the app, choose <strong>Open</strong>, then confirm <strong>Open</strong> again in the dialog. You only need to do this once.</p>
      <div class="kb-tip">💡 Apple Silicon and Intel Macs are both supported.</div>
    </div>

    <div class="kb-article" id="budget">
      <h2>Budget page</h2>
      <p>The Budget page shows your monthly income and expenses side by side. Every expense row tracks how much you've spent so far this month from your imported transactions.</p>
      <h3>Adding expenses</h3>
      <p>Click <strong>+ Add expense</strong> and type the name and amount. Groundwork automatically matches it to your transactions.</p>
      <h3>Sinking funds</h3>
      <p>Sinking funds are savings goals you contribute to monthly — like a car repair fund or vacation savings. Add one from the Budget page and Groundwork tracks your progress automatically.</p>
    </div>

    <div class="kb-article" id="debt">
      <h2>Debt tracker</h2>
      <p>The Debt page is where Groundwork earns its keep. Add every debt you have — credit cards, car loans, student loans, leases — and Groundwork builds a payoff schedule.</p>
      <h3>Debt types</h3>
      <ul>
        <li><strong>Credit card:</strong> Balance, APR, minimum payment, due date</li>
        <li><strong>Loan:</strong> Balance, APR, payment, start date, term</li>
        <li><strong>Lease:</strong> Monthly payment, start date, lease end date</li>
      </ul>
      <h3>Snowball vs Avalanche</h3>
      <p><strong>Snowball</strong> pays off the smallest balance first — gives you quick wins and momentum.</p>
      <p><strong>Avalanche</strong> pays off the highest interest rate first — saves the most money mathematically.</p>
      <p>Both work. Pick the one you'll actually stick to.</p>
      <div class="kb-tip">💡 When a card is paid off, Groundwork adds the freed minimum to your next debt automatically — that's the snowball/avalanche effect.</div>
      <h3>Logging charges &amp; payments</h3>
      <p>You can record activity directly on a debt card — charges, payments, and interest — with a running total, so the balance reflects what you've actually done rather than just its starting figure. Link a payment to the matching transaction in your checking account (from either the debt ledger or the main Ledger) and Groundwork keeps both records in sync, with no double-entry. Unlinking later leaves both records intact.</p>
      <h3>Recurring payments</h3>
      <p>For a payment you make every month, save the pattern once. Each month Groundwork prepares a draft you can confirm, edit, or skip — no re-entering the same payment over and over. Because these payments move the account balance, your payoff projection reflects what you've really paid.</p>
    </div>

    <div class="kb-article" id="ledger">
      <h2>Ledger</h2>
      <p>The Ledger is your full transaction history. Every imported transaction appears here, categorized and searchable.</p>
      <h3>Categorizing transactions</h3>
      <p>Click any transaction to change its category. Groundwork remembers your choice and applies it to similar transactions in future imports.</p>
      <h3>Splitting transactions</h3>
      <p>If a transaction covers multiple categories (like a Target run that included groceries and clothing), click the transaction and choose <strong>Split</strong>.</p>
      <h3>Reconciling</h3>
      <p>Click the checkmark on any transaction to mark it as cleared — confirmed against your bank statement.</p>
    </div>

    <div class="kb-article" id="networth">
      <h2>Net worth tracker</h2>
      <p>Net worth = everything you own minus everything you owe. Groundwork tracks it over time so you can see the trend.</p>
      <p>Your checking and savings balances pull automatically from your imported transactions. Enter your home value, retirement accounts, investments, and mortgage balance manually or link them.</p>
      <div class="kb-tip">💡 Take a snapshot at the end of each month. After a few months you'll see the line going up — that's the most motivating thing in the whole app.</div>
    </div>

    <div class="kb-article" id="gifts">
      <h2>Gift budget</h2>
      <p>The Gift page helps you plan gifts for everyone in your life without getting blindsided.</p>
      <h3>Adding people</h3>
      <p>Click <strong>+ Person</strong> and add the people you buy gifts for. Tag them as Family, Friend, Coworker, or Other.</p>
      <h3>Adding occasions</h3>
      <p>Each person can have multiple occasions — Birthday, Anniversary, Christmas, Mother's Day, etc. Each occasion has a date and a budget.</p>
      <h3>Coming up</h3>
      <p>The top of the page shows everyone with an occasion in the next 90 days. Click <strong>Budget it</strong> to add their gift to this month's budget automatically.</p>
      <h3>Seasonal funds</h3>
      <p>For Christmas, vacations, or any recurring occasion, create a Seasonal Fund with a target amount and a funded-by date. Groundwork tells you how much to save each month to hit it.</p>
    </div>

    <div class="kb-article" id="investments">
      <h2>Investments</h2>
      <p>The Investments page tracks your holdings — stocks, ETFs, and other positions — with their cost basis and current value, and prices update automatically. Your total rolls into your Net Worth.</p>
      <h3>Adding holdings</h3>
      <p>Add each position with its symbol, number of shares, and what you paid. Groundwork shows your gain or loss and keeps the value current.</p>
      <div class="kb-tip">💡 While you're carrying high-interest debt, paying down a card is a guaranteed return at that card's APR — often more than the market averages. Groundwork points this out on the Debt Payoff page so you can decide where an extra dollar does the most work.</div>
    </div>

    <div class="kb-article" id="reports">
      <h2>Reports</h2>
      <p>The Report Center has built-in reports, several of which can include an AI-written narrative.</p>
      <ul>
        <li><strong>Distance Traveled</strong> — the ground you've covered: principal paid down, debts retired, cash flow freed, and how much closer your debt-free date has moved</li>
        <li><strong>Monthly Spending Summary</strong> — income, expenses, budget vs. actual, and how the month stacks up</li>
        <li><strong>Category Deep-Dive</strong> — the trend for any category over any date range, plus top merchants</li>
        <li><strong>Spending vs. Budget</strong> — how a month's spending compared to your budgeted amounts</li>
        <li><strong>Annual Summary</strong> — a full year of income, expenses, and top categories, month by month</li>
        <li><strong>Debt Payoff Analysis</strong> — balances, APRs, payoff sequence, interest cost, and freed minimums</li>
        <li><strong>Debt Progress</strong> — balance history per card, interest paid to date, payoff trajectory</li>
        <li><strong>Income &amp; Savings Rate</strong> — income, expenses, and your savings rate against a 15–20% target</li>
        <li><strong>Net Worth Timeline</strong> — your net worth over time, assets vs. liabilities, payoff milestones</li>
        <li><strong>Import Audit</strong> — transaction counts, categorization rate, duplicates, and what landed in Other</li>
      </ul>
      <p>Every report has a Print button. The narrative reports (such as the Monthly Spending Summary and Distance Traveled) are written by AI, on your own machine. See <a href="#ai">AI features</a>.</p>
    </div>

    <div class="kb-article" id="byb">
      <h2>Before You Buy</h2>
      <p>Thinking about a big purchase? Enter its name and cost on the Before You Buy page, and Groundwork shows exactly what it does to your monthly budget and your debt-free date.</p>
      <p>It isn't there to talk you out of anything — it's there to make sure you know the real cost, in dollars and in time, before you decide.</p>
    </div>

    <div class="kb-article" id="trip">
      <h2>Trip Planner</h2>
      <p>The Trip Planner helps you plan a trip that actually fits your finances. Enter your destination, dates, and whether you're flying or driving.</p>
      <p>Groundwork estimates the cost from real inputs — your monthly surplus, your vehicle's MPG and current gas prices if you're driving, your actual dining history for meals, plus hotel and activity estimates — and shows what the trip costs in debt-free days, so you can decide with your eyes open.</p>
      <div class="kb-tip">💡 For a trip that's months out, pair this with a Seasonal Fund (see <a href="#gifts">Gift budget</a>) so the money is set aside by the time you go.</div>
    </div>

    <div class="kb-article" id="backup">
      <h2>Backups</h2>
      <p>Your data is stored locally at:</p>
      <ul>
        <li><strong>Windows:</strong> %LOCALAPPDATA%/Groundwork/groundwork.db</li>
        <li><strong>Mac:</strong> ~/Library/Application Support/Groundwork/groundwork.db</li>
        <li><strong>Linux:</strong> ~/.local/share/Groundwork/groundwork.db</li>
      </ul>
      <p>To back up manually, go to <strong>Settings → Data & Backup → Back up now</strong>. This creates a timestamped copy you can save anywhere.</p>
      <div class="kb-tip">💡 Copy your .db file to a USB drive or cloud folder (Dropbox, Google Drive) regularly. It's just one file.</div>
    </div>

    <div class="kb-article" id="ai">
      <h2>AI features</h2>
      <p>Groundwork can write a plain-English monthly report and other narrative insights. AI is completely optional, and it runs <strong>only on your own machine</strong>.</p>
      <h3>Local AI (free, fully private)</h3>
      <p>Groundwork runs AI <strong>on your own machine</strong>, with a language model that comes inside the installer and runs inside Groundwork itself: there is no separate program to install, nothing ever leaves your computer, there's no API key, and there's no cost. Turn it on when Groundwork first asks, or later under <strong>Settings → AI features</strong>. Local AI needs at least 8 GB of memory; on a smaller computer AI stays off, and every other feature of Groundwork works fully either way.</p>
      <h3>No cloud AI</h3>
      <p>Groundwork has no cloud AI option. <strong>Nothing is sent to an AI service, ever.</strong> If a computer can't comfortably run a local model, AI features simply stay off; budgets, debt payoff and reports all work the same. Reading PDF statements needs the local model too; without it, import your bank's CSV or QFX download instead.</p>
    </div>

    <div class="kb-article" id="privacy">
      <h2>Privacy & your data</h2>
      <p>Groundwork is built on one principle: <strong>your financial data is yours.</strong></p>
      <ul>
        <li>Your database lives on your machine. We never see it.</li>
        <li>No account required. No login.</li>
        <li>No telemetry, no analytics, no usage tracking.</li>
        <li>The app runs on localhost — only your machine can access it.</li>
        <li>AI runs only on your machine: nothing is sent to an AI service. See <a href="/privacy">the privacy policy</a> for the few requests the app does make, and what each one sends.</li>
        <li>Uninstalling Groundwork does not delete your data — it stays in AppData until you delete it yourself.</li>
      </ul>
    </div>

    <div class="kb-article" id="report-bug">
      <h2>Reporting a bug</h2>
      <p>Groundwork is actively maintained. If something breaks:</p>
      <p>1. In the app, click <strong>⚑ Report</strong> in the top bar.</p>
      <p>2. Describe what you were doing when it broke.</p>
      <p>3. Click <strong>Open in mail app</strong>. Your email app opens with the report filled in, addressed to support@groundworkfinance.app. Read it over and send it yourself: nothing is sent without you.</p>
      <p>Or just email <a href="mailto:support@groundworkfinance.app">support@groundworkfinance.app</a> directly.</p>
    </div>

  </div>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Knowledge Base',
        description='Help and documentation for Groundwork — installation, importing transactions, budgeting, debt payoff, and every feature explained.',
        canonical=SITE_URL + '/knowledge-base'
    )

# ── About page ────────────────────────────────────────────────────────────────
@app.route('/about')
def about():
    content = """
<section class="page-head">
  <h1>About Groundwork</h1>
  <p>A free personal finance app with nothing to sell you, and why it exists.</p>
</section>
<div class="narrow prose">
  <h2>Our horizon</h2>
  <p>The goal of Groundwork is <span class="fi">financial independence, for everyone</span> who uses it: to reach the point where their
    money supports the life they choose. Groundwork can't promise anyone gets there. What it can do is
    show you where you stand, explain how each number was made, and help you see the next step, whatever your
    starting point.</p>

  <h2>Why Groundwork exists</h2>
  <p>Most finance apps are built around something they want to sell: a card, a loan, a premium tier, or your
    attention. The advice and the product come from the same place, and it's hard to tell which one is talking.</p>
  <p>Groundwork has nothing behind the advice. It tracks your money, explains what it shows you, and leaves the
    decisions to you. The software is the product, not you.</p>

  <h2>Where it started</h2>
  <p>Groundwork started as a tool for one family trying to get their finances under control: track the spending,
    build a plan for the debt, and see a date when things would be different. It grew into a full finance app:
    budget, ledger, net worth, investments, gifts, trips, reports, and the planning that ties them together.</p>
  <p>It's built for everyone, whatever their situation, whether you're paying down a card or deciding where your
    savings should go.</p>

  <h2>Why it's free</h2>
  <p>Because the people who need it most shouldn't have to pay for it. Groundwork is free to download and use, with no
    account, no subscription and no ads. Your data stays on your computer.</p>

  <h2>Telling us something's wrong</h2>
  <p>Groundwork sends no telemetry, so we only hear about a problem if you tell us. In the app, the
    <strong>⚑ Report</strong> button opens your own email app with a report filled in; you read it over and send it
    yourself. Nothing is sent without you. You can also email
    <a href="mailto:support@groundworkfinance.app">support@groundworkfinance.app</a> directly.</p>
  <p>We read every one.</p>
  <p class="callout" style="font-family:'Fraunces',Georgia,serif;font-style:italic;font-size:clamp(15px,4.6vw,22px);margin-top:36px"><span class="fi">Financial independence for everyone,</span> one understood decision at a time.</p>
  <p style="margin-top:20px"><a href="/download" class="btn btn-primary">Download Groundwork free →</a></p>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='About',
        description='Groundwork is a free personal finance app that tracks your whole financial picture, explains it, and has nothing to sell you.',
        canonical=SITE_URL + '/about'
    )

# ── Privacy page ──────────────────────────────────────────────────────────────
@app.route('/privacy')
def privacy():
    content = """
<section class="page-head">
  <h1>Privacy Policy</h1>
  <p>What stays on your computer, what leaves it, and why.</p>
</section>
<div class="narrow prose">
  <p style="color:var(--muted)">Last updated: October 12, 2026. This page describes Groundwork """ + SITE_VERSION + """, the version offered for download.</p>

  <h2>Your data stays on your machine</h2>
  <p>Groundwork is a desktop application. Your financial data — transactions, balances,
    budgets, debt information — is stored in a SQLite database on your computer.
    We have no access to it. It never leaves your machine unless you explicitly export it.</p>
  <p>The app sends no telemetry, no analytics and no usage tracking.</p>

  <h2>What Groundwork sends, and why</h2>
  <p>A few features need a fact from outside your computer. None of these requests carries your balances,
    transactions, amounts, names or account details:</p>
  <ul>
    <li><strong>The update check</strong> asks this website whether a newer version exists. It sends no version
      number and nothing about you.</li>
    <li><strong>Investment prices</strong> send the ticker symbols you hold (for example VOO) to Yahoo Finance.</li>
    <li><strong>Utility and fuel prices</strong> send your state to the U.S. Energy Information Administration, which
      publishes the prices. Groundwork asks for your state; it never looks up your location.</li>
    <li><strong>Trip distances</strong> send the places you type into the trip planner to OpenStreetMap, to work out
      the driving distance.</li>
  </ul>

  <h2>Websites opened inside Groundwork</h2>
  <p>Groundwork can open your bank's website, and Google Flights, in a separate private window. That
    window keeps no sign-in after it closes, and anything you type there goes to that website under
    its own privacy policy, not to us. Groundwork does not read those pages, with one exception: in
    the Google Flights window, when you click <em>Continue</em> to choose a fare, Groundwork reads the
    price on that button and asks whether to use it in your trip budget. Nothing else on the page is
    read or kept, the price stays on your computer, and it is used only if you say yes.</p>

  <h2>AI features</h2>
  <p>Groundwork's AI features are optional and run <strong>only on your own machine</strong>: the
    model comes with Groundwork and runs inside it, so nothing is sent to an AI service and no API
    key exists. There is no cloud AI option.</p>

  <h2>The Report button</h2>
  <p>The <strong>⚑ Report</strong> button opens your own email app with a report filled in. Nothing is sent unless
    you send that email yourself.</p>

  <h2>This website</h2>
  <ul>
    <li><strong>Counters, not tracking.</strong> The site keeps one count per page per day, and one count per
      download platform per day. It stores no IP address, no cookie and no browser details.</li>
    <li><strong>Email updates.</strong> If you sign up, we store your name and email address to send you product
      updates, delivered through SendGrid. We never sell or share your email address.</li>
    <li><strong>Unsubscribing.</strong> Every update email carries a one-click unsubscribe link. You can also email
      <a href="mailto:hello@groundworkfinance.app">hello@groundworkfinance.app</a>.</li>
  </ul>

  <h2>Contact</h2>
  <p>Questions about privacy? Email <a href="mailto:hello@groundworkfinance.app">hello@groundworkfinance.app</a></p>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Privacy Policy',
        description='Groundwork stores your financial data on your computer: no account, no cloud, no telemetry. Here is exactly what leaves your computer, and why.',
        canonical=SITE_URL + '/privacy'
    )

# ── Terms of Use / EULA ───────────────────────────────────────────────────────
# Mirrors EULA.txt (the text shown in the installer and in-app). Keep the two
# in sync when either changes.
@app.route('/terms')
def terms():
    content = """
<section class="page-head">
  <h1>Terms of Use &amp; License</h1>
  <p>The licence for Groundwork, the same text the installer and the app show.</p>
</section>
<div class="container" style="max-width:760px;padding:60px 24px">
  <p style="color:var(--slate);margin-bottom:8px">End User License Agreement · Version 1.2 · Effective October 8, 2026</p>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:32px">
    By installing, accessing, or using Groundwork (the "Software"), you agree to this
    End User License Agreement and Terms of Use (the "Agreement"). If you do not agree,
    do not install or use the Software.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">1. License grant</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    Groundwork is free software provided at no charge. Subject to your compliance with this
    Agreement, you are granted a personal, non-exclusive, non-transferable, revocable license
    to install and use the Software for your own personal or internal purposes. You may not
    sell, rent, lease, sublicense, or charge a fee for the Software; redistribute a modified
    version; remove or alter any proprietary notices; or represent a modified copy as the
    official Software. All rights not expressly granted are reserved by the publisher.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">2. Ownership</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    The Software is licensed, not sold. The publisher retains all right, title, and interest
    in the Software, including all intellectual property rights. The data you enter or import
    remains yours.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">3. Your responsibility — verify all figures</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:16px">
    Groundwork is a personal budgeting and planning aid. It performs calculations and organizes
    information you enter or import, but it is <strong>not a system of record</strong> and is not
    a substitute for your bank, lender, or financial institution.
  </p>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:16px;font-weight:600">
    You are solely responsible for verifying the accuracy of all balances, transactions,
    categorizations, interest figures, payoff projections, and any other outputs of the Software
    against the official statements and records provided by your bank, lender, or other financial
    institution before relying on them or making any financial decision.
  </p>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    Imported data may be incomplete, delayed, duplicated, mis-categorized, or otherwise
    inaccurate. Calculations and projections are estimates. Always confirm your true available
    funds directly with your financial institution before spending, transferring, or committing
    money.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">4. Not professional advice</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    The Software and its outputs — including any AI-generated reports, summaries, or suggestions —
    are provided for informational purposes only and do not constitute financial, investment, tax,
    accounting, or legal advice, and are not a recommendation to take or refrain from any action.
    Consult a qualified professional before making financial decisions.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">5. Disclaimer of warranties</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    THE SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTY OF ANY KIND, WHETHER
    EXPRESS, IMPLIED, OR STATUTORY, INCLUDING THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS
    FOR A PARTICULAR PURPOSE, ACCURACY, AND NON-INFRINGEMENT. The publisher does not warrant that
    the Software will be error-free, uninterrupted, or accurate. You use the Software at your own
    risk.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">6. Limitation of liability</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE PUBLISHER WILL NOT BE LIABLE FOR ANY INDIRECT,
    INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR FOR ANY LOSS OF MONEY, FUNDS,
    PROFITS, DATA, OR GOODWILL, ARISING OUT OF OR RELATED TO YOUR USE OF, OR INABILITY TO USE, THE
    SOFTWARE — INCLUDING ANY FINANCIAL DECISION MADE IN RELIANCE ON IT. Because the Software is
    provided free of charge, the publisher's total aggregate liability shall not exceed US $0.
    Some jurisdictions do not allow certain limitations, so some of the above may not apply to you.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">7. AI features</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    The Software's AI features are optional. They run only on your own computer, using a local
    model. The Software does not send your data to any AI service, and it has no option to do so.
    If your computer cannot run a local model, the AI features are unavailable and the rest of the
    Software works as described. AI outputs may be inaccurate or incomplete and are subject to
    Sections 3 and 4.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">8. Privacy</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:12px">
    Your financial data is stored locally on your device. The publisher does not collect or
    receive it.
  </p>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:12px">
    Some features open a third-party website in a separate, private window inside the Software:
    your bank's website, and Google Flights. Anything you enter on such a website goes to that
    website, under its own terms and privacy policy. The Software does not read those pages, with
    one exception: in the Google Flights window, when you click a "Continue" button to choose a
    fare, the Software reads the price shown on that button so that it can offer to use it in your
    trip budget. It reads nothing else from the page, keeps nothing else, and uses the price only if
    you confirm it. That price is Google's figure; the airline's final price may be higher, and
    Section 3 applies to it.
  </p>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    See the <a href="/privacy">Privacy Policy</a> for details.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">9. Termination</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    This license is effective until terminated and terminates automatically if you breach it. You
    may terminate it at any time by uninstalling and deleting the Software. Sections 3 through 6
    and 10 survive termination.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">10. Governing law</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    This Agreement is governed by the laws of the State of Ohio, USA, without regard to its
    conflict-of-laws rules, except where your local law requires otherwise.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">11. Changes to this Agreement</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    The publisher may update this Agreement for future versions of the Software. Continued use of
    an updated version after the changes take effect constitutes acceptance of the revised
    Agreement.
  </p>

  <h2 style="font-size:20px;font-weight:700;margin-bottom:10px">12. Contact</h2>
  <p style="color:var(--slate);line-height:1.9">
    Questions about this Agreement? Email
    <a href="mailto:support@groundworkfinance.app">support@groundworkfinance.app</a>
  </p>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Terms of Use',
        description='Groundwork Terms of Use and End User License Agreement. Groundwork is a free planning aid; you are responsible for verifying all figures against your bank.',
        canonical=SITE_URL + '/terms'
    )

# ── Features page ─────────────────────────────────────────────────────────────
@app.route('/features')
def features():
    content = _icons("""
<section class="page-head">
  <h1>Everything in Groundwork</h1>
  <p>One app for your whole financial picture, in the version you can download today.</p>
</section>
<div class="band" style="padding-top:56px">
  <div class="container">
    <div class="features-grid" style="margin-top:0">
      <div class="feature-card"><span class="chip chip-pine">[[wallet]]</span><h3>Budget</h3>
        <p>Monthly income and expense lines, each shown against what you've actually spent this month from your imported transactions.</p></div>
      <div class="feature-card"><span class="chip chip-pine">[[list]]</span><h3>Ledger</h3>
        <p>Your full transaction history, sorted into categories, searchable, with split transactions and reconciliation.</p></div>
      <div class="feature-card"><span class="chip chip-pine">[[import]]</span><h3>Import from your bank</h3>
        <p>CSV, OFX, QFX and QIF files from your bank, or your history from Quicken. Duplicates are skipped and categories are remembered.</p></div>
      <div class="feature-card"><span class="chip chip-ember">[[card]]</span><h3>Debt payoff</h3>
        <p>Snowball or avalanche. Groundwork lays out the payoff order and your debt-free date, and logs charges and payments on each debt.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[trend]]</span><h3>Net worth</h3>
        <p>Everything you own minus everything you owe, saved month by month so you can see the trend.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[chart]]</span><h3>Investments</h3>
        <p>Your holdings with what you paid and what they're worth at their latest price, rolled into your net worth.</p></div>
      <div class="feature-card"><span class="chip chip-ember">[[heart]]</span><h3>Health care spending</h3>
        <p>Pharmacy, doctor, dental and similar costs are tracked as their own category, and Groundwork doesn't suggest cutting them.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[gift]]</span><h3>Gift budget</h3>
        <p>Every person and occasion in one list, with seasonal funds for the big ones.</p></div>
      <div class="feature-card"><span class="chip chip-ink">[[plane]]</span><h3>Trip planner</h3>
        <p>A trip priced from your own numbers: your car's mileage and gas prices if you drive, Google Flights if you fly.</p></div>
      <div class="feature-card"><span class="chip chip-ink">[[cart]]</span><h3>Before You Buy</h3>
        <p>What a big purchase does to your budget and your debt-free date, before you commit.</p></div>
      <div class="feature-card"><span class="chip chip-pine">[[file]]</span><h3>Reports</h3>
        <p>Built-in reports on spending, budget against actual, debt progress and net worth over time. Print any of them.</p></div>
      <div class="feature-card"><span class="chip chip-gold">[[spark]]</span><h3>Local AI, optional</h3>
        <p>Plain-English write-ups of your month from a model that runs on your own computer. No key, nothing sent out.</p></div>
      <div class="feature-card"><span class="chip chip-ink">[[lock]]</span><h3>Private by design</h3>
        <p>No account, no cloud, no subscription, no telemetry. Your data lives in one file on your computer.</p></div>
    </div>
    <div class="center" style="margin-top:56px;display:flex;gap:14px;justify-content:center;flex-wrap:wrap">
      <a href="/download" class="btn btn-primary">Download free for <span class="os-download-label">Windows</span> →</a>
      <a href="/coming" class="btn btn-ghost">See what's coming in 2.0 →</a>
    </div>
  </div>
</div>
""")
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Features',
        description='Budget, ledger, debt payoff, net worth, investments, health care spending, gifts, trips and reports: everything Groundwork does, in one free app.',
        canonical=SITE_URL + '/features'
    )


# ── Coming in 2.0 (WEBSITE_MESSAGE.md W3, §6.1) ────────────────────────────────
# Every card describes something built and accepted in 2.0 (W5); the one thing only designed says so.
@app.route('/coming')
def coming():
    content = _icons("""
<section class="hero next-hero">
  <div class="hero-center">
    <div class="beta-badge"><b></b> Being built and tested now</div>
    <h1>Coming in <em>Groundwork 2.0</em></h1>
    <p class="lead">The biggest update we've ever built. Groundwork 2.0 does more of the work for you, explains more of
      what it finds, and still keeps every number on your own computer, all toward one horizon: <span class="fi">financial independence, for everyone</span>. Here's what's on the way.</p>
    <div class="hero-btns"><a href="#signup" class="btn btn-gold">Tell me when it ships</a>
      <a href="/download" class="btn btn-ghost-light">Get """ + SITE_VERSION + """ today</a></div>
  </div>
</section>

<section class="band" style="padding-top:64px">
  <div class="container">
    <div class="next-grid" style="margin-top:0">
      <div class="next-card reveal"><span class="chip chip-pine">[[bank]]</span><h3>Your statements, with one press</h3>
        <p>No more logging in to download files. Tell Groundwork which bank you use, and when you ask, it opens your bank's
        website in a window inside Groundwork and brings your statements back for you to review. It only goes when you ask,
        never on its own or on a schedule. Your password stays in your computer's own secure vault, not in Groundwork.</p></div>
      <div class="next-card reveal"><span class="chip chip-ember">[[bill]]</span><h3>Your bills, read straight from the biller</h3>
        <p>Groundwork can read what a bill says on the company's own website, like the amount and the due date, and put it
        right next to that line in your budget. You confirm it before it's used. And Groundwork never presses a Pay button:
        paying is always yours.</p></div>
      <div class="next-card reveal"><span class="chip chip-gold">[[ask]]</span><h3>Ask why</h3>
        <p>A number looks wrong? Ask. Groundwork checks your own records and tells you what it found: a payment filed in the
        wrong place, a deposit that isn't counted as income, a month with nothing imported. If there's a fix, you see exactly
        what would change before anything does, and every fix can be undone.</p></div>
      <div class="next-card reveal"><span class="chip chip-pine">[[pay]]</span><h3>Your pay, employer by employer</h3>
        <p>Groundwork reads each paycheck on its own. If one stops showing up or drops, it tells you plainly and shows a few
        ways the month could go from there. If your pay changes with overtime or holiday pay, it asks once, so a slow week is
        never mistaken for a pay cut.</p></div>
      <div class="next-card reveal"><span class="chip chip-ink">[[fork]]</span><h3>Possible futures</h3>
        <p>See your next twelve months side by side: as things are, and what happens if your most expensive months come back,
        a month goes by without income, or you pay only the minimums. Every future says what it assumes. If one doesn't fit
        your life, tell it what's missing and they all recalculate.</p></div>
      <div class="next-card reveal"><span class="chip chip-gold">[[cal]]</span><h3>A monthly review and a Sunday check-in</h3>
        <p>When a month's records are complete, Groundwork writes up what happened: what came in, what went out, and how it
        compares. Every Sunday, a short check-in looks back at your week and ahead to the next one: a paycheck due, a bill
        coming up.</p></div>
      <div class="next-card reveal"><span class="chip chip-ink">[[cart]]</span><h3>Before You Buy, with the whole cost</h3>
        <p>Thinking about a big purchase? See what it really costs each month, interest included, and whether financing it
        costs more than paying down what you already owe. We're not here to talk you out of anything. We show you the
        numbers.</p></div>
      <div class="next-card reveal"><span class="chip chip-ink">[[plane]]</span><h3>Trips, priced from real fares</h3>
        <p>The trip planner opens Google Flights and Google Hotels right inside Groundwork and uses the price you pick.
        Haven't picked one yet? It uses the government's average fare for that route instead of a guess.</p></div>
      <div class="next-card reveal"><span class="chip chip-gold">[[gift]]</span><h3>Gifts, as the yearly cost they are</h3>
        <p>Birthdays and holidays come every year. Groundwork adds up the next twelve months of them and shows what to set
        aside each month, so December never arrives as a surprise.</p></div>
      <div class="next-card reveal"><span class="chip chip-ember">[[flame]]</span><h3>Utilities and fuel, from public prices</h3>
        <p>Groundwork estimates your gas, electric, propane, heating oil and gasoline costs from the U.S. government's
        published prices for your state. It asks which state you're in and never looks up your location.</p></div>
      <div class="next-card reveal"><span class="chip chip-pine">[[micro]]</span><h3>Research, shown honestly</h3>
        <p>Where a well-known study backs up an idea, like saving automatically, Groundwork shows you what the study found
        and what it doesn't show.</p></div>
      <div class="next-card reveal"><span class="chip chip-ink">[[cpu]]</span><h3>An assistant that lives on your computer</h3>
        <p>The AI ships inside Groundwork and runs on your own machine. Nothing you ask it is sent anywhere. Every page still
        works with the AI turned off, and a log shows you exactly what the assistant was given.</p></div>
      <div class="next-card reveal"><span class="chip chip-gold">[[math]]</span><h3>Every number shows its working</h3>
        <p>Groundwork shows where its figures come from: the inputs, the math, and any assumption behind them. If it can't
        show how it got a number, it doesn't show you the number.</p></div>
      <div class="next-card reveal"><span class="chip chip-pine">[[eye]]</span><h3>Easier on the eyes</h3>
        <p>We checked every piece of text against every background, so nothing in Groundwork is too faint to read.</p></div>
      <div class="next-card design reveal"><span class="chip chip-ember">[[pulse]]</span><h3>Health care costs <span class="tag tag-design">In design</span></h3>
        <p>We're designing a health care section that tracks your bills against your insurance statements and follows your
        deductible through the year. It's in design, not built yet, and it will follow the same rule as the rest of
        Groundwork: nothing about your health leaves your computer.</p></div>
    </div>
    <p class="center" style="margin-top:52px;font-family:'Fraunces',Georgia,serif;font-style:italic;font-size:clamp(16px,4.8vw,30px);color:var(--ink)"><span class="fi">Financial independence for everyone,</span> <span class="fi">one understood decision at a time.</span></p>
    <p class="center" style="margin-top:14px;color:var(--slate)"><em>Groundwork 2.0 isn't in the download yet. When it is, you'll see it here first.</em></p>
  </div>
</section>
<div id="signup"></div>
""") + SIGNUP_BAND
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Coming in Groundwork 2.0',
        description='Groundwork 2.0 is being built now: statements with one press, bills read from the biller, Ask why, possible futures, a Sunday check-in and more, all on your own computer.',
        canonical=SITE_URL + '/coming'
    )


# ── Signup page ───────────────────────────────────────────────────────────────
# Email-updates signup, linked from the footer and the signup form.
@app.route('/signup')
def signup():
    content = """
<section class="signup-section" style="min-height:62vh;display:flex;align-items:center">
  <div class="container">
    <h2>Get Groundwork updates</h2>
    <p>One email when something worth knowing ships, including Groundwork 2.0. No spam, and every email has a one-click unsubscribe.</p>
    <div class="signup-form">
      <input type="text" id="signup-name" placeholder="Your name" style="max-width:170px" aria-label="Your name">
      <input type="email" id="signup-email" placeholder="Your email address" aria-label="Your email address">
      <button class="btn" onclick="submitSignup()">Notify me →</button>
    </div>
    <div class="signup-msg" id="signup-msg"></div>
  </div>
</section>
""" + SIGNUP_SCRIPT
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Sign up for updates',
        description="Get notified about new Groundwork releases, including Groundwork 2.0. No spam, unsubscribe any time.",
        canonical=SITE_URL + '/signup'
    )

# ── Update manifest (Phase 2 dependency) ──────────────────────────────────────
# The desktop app's update check reads this URL. Flask owns all routes here,
# so without this the update channel 404s. The manifest lives on disk next to
# the subscriber DB so publishing an update = editing a JSON file, no redeploy.
@app.route('/version.json')
def version_json():
    manifest = DB_PATH.parent / 'version.json'
    try:
        payload = manifest.read_text(encoding='utf-8')
    except OSError:
        return jsonify({'error': 'version manifest not published yet'}), 404
    resp = app.response_class(payload, mimetype='application/json')
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


# ── Changelog ─────────────────────────────────────────────────────────────────
# The version banner in the update popup only names the newest release.
# /changelog renders full history for testers checking "what changed" and for
# prospective downloaders sizing up whether the project is alive. Same
# single-file publish model as version.json: edit changelog.json, done.
@app.route('/changelog')
def changelog():
    from datetime import datetime as _dt
    path = DB_PATH.parent / 'changelog.json'
    try:
        import json as _j
        entries = _j.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        entries = []

    if not entries:
        body = """
<div class="container" style="max-width:720px;padding:60px 24px">
  <h1 style="font-size:32px;font-weight:800;margin-bottom:8px">Changelog</h1>
  <p style="color:var(--slate)">First public release coming soon.</p>
</div>"""
    else:
        def fmt_date(s):
            try:    return _dt.strptime(s, '%Y-%m-%d').strftime('%B %-d, %Y')
            except Exception: return s
        def render_bullets(items, tag_color):
            return ''.join(
                f'<li style="margin-bottom:6px">{h(x)}</li>' for x in (items or [])
            )
        cards = ''
        for e in entries:
            date_str  = fmt_date(e.get('date',''))
            version   = h(e.get('version',''))
            headline  = h(e.get('headline',''))
            fixed     = e.get('fixed',    []) or []
            added     = e.get('added',    []) or []
            improved  = e.get('improved', []) or []
            section = lambda label, items, color: (f"""
              <div style="margin-top:14px">
                <div style="font-size:11px;font-weight:700;letter-spacing:.08em;
                            text-transform:uppercase;color:{color};margin-bottom:6px">
                  {label}</div>
                <ul style="color:var(--ink);line-height:1.7;font-size:14px;padding-left:20px">
                  {''.join(f'<li style="margin-bottom:4px">{h(x)}</li>' for x in items)}
                </ul>
              </div>""" if items else '')
            cards += f"""
            <article style="background:#fff;border:1px solid var(--steel);border-radius:12px;
                            padding:28px;margin-bottom:20px">
              <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:6px">
                <span style="font-family:'DM Mono',monospace;font-size:13px;font-weight:600;
                             color:var(--pine)">{version}</span>
                <span style="font-size:12px;color:var(--slate)">{date_str}</span>
              </div>
              {'<h2 style=\"font-size:20px;font-weight:700;margin-bottom:4px\">'+headline+'</h2>' if headline else ''}
              {section('Fixed',    fixed,    'var(--ember)')}
              {section('Added',    added,    'var(--pine)')}
              {section('Improved', improved, '#8b5cf6')}
            </article>"""
        body = f"""
<div class="container" style="max-width:720px;padding:60px 24px">
  <div class="section-label">What's changed</div>
  <h1 style="font-size:40px;font-weight:600;margin-bottom:8px">Changelog</h1>
  <p style="color:var(--slate);margin-bottom:36px">
    Every release, shipped honest and dated.
    <a href="/download">Download</a> the latest to get all of the below.
  </p>
  {cards}
</div>"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', body),
        title='Changelog',
        description='Everything shipped in Groundwork, honest and dated — bug fixes, new features, and platform availability updates.',
        canonical=SITE_URL + '/changelog'
    )

# ── SEO: sitemap + robots ─────────────────────────────────────────────────────
# Served by Flask (not Nginx static config) so they exist wherever this app
# runs, with no separate file to deploy or forget. The static sitemap.xml in
# the repo is kept in sync as a fallback in case Nginx is ever set to serve
# statics first. Add new public pages HERE — the sitemap generates from this
# list, so it can never silently go stale the way the old 3-entry file did.
_SITEMAP_PAGES = [
    # (path, changefreq, priority)
    ('/',               'weekly',  '1.0'),
    ('/download',       'weekly',  '0.9'),
    ('/signup',         'monthly', '0.9'),
    ('/features',       'monthly', '0.8'),
    ('/coming',         'weekly',  '0.8'),
    ('/knowledge-base', 'weekly',  '0.7'),
    ('/about',          'monthly', '0.6'),
    ('/changelog',      'weekly',  '0.5'),
    ('/privacy',        'yearly',  '0.3'),
    ('/terms',          'yearly',  '0.3'),
]

@app.route('/sitemap.xml')
def sitemap_xml():
    urls = '\n'.join(
        f'  <url>\n'
        f'    <loc>{SITE_URL}{path}</loc>\n'
        f'    <changefreq>{freq}</changefreq>\n'
        f'    <priority>{prio}</priority>\n'
        f'  </url>'
        for path, freq, prio in _SITEMAP_PAGES
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f'{urls}\n'
           '</urlset>\n')
    resp = app.response_class(xml, mimetype='application/xml')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp

@app.route('/robots.txt')
def robots_txt():
    # Token URLs (confirm/unsubscribe) and the admin panel have no business
    # in a search index; everything else is fair game.
    body = ('User-agent: *\n'
            'Disallow: /admin\n'
            'Disallow: /confirm/\n'
            'Disallow: /unsubscribe/\n'
            'Allow: /\n'
            '\n'
            f'Sitemap: {SITE_URL}/sitemap.xml\n')
    resp = app.response_class(body, mimetype='text/plain')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp

# ── API: Signup ───────────────────────────────────────────────────────────────
@app.route('/api/signup', methods=['POST'])
def api_signup():
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    name  = (data.get('name') or '').strip()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'message': 'Enter a valid email address.'})
    token = secrets.token_urlsafe(32)
    try:
        with get_db() as db:
            db.execute(
                'INSERT INTO subscribers (email, name, token) VALUES (?,?,?)',
                (email, name, token)
            )
            db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'ok': True, 'message': "You're already on the list! Check your inbox."})
    send_confirmation_email(email, name, token)
    return jsonify({'ok': True,
                    'message': "✓ Check your email and click the confirmation link."})

# ── Confirm subscription ──────────────────────────────────────────────────────
@app.route('/confirm/<token>')
def confirm(token):
    with get_db() as db:
        row = db.execute(
            'SELECT * FROM subscribers WHERE token=?', (token,)
        ).fetchone()
        if not row:
            return "<h2>Invalid or expired link.</h2>", 400
        if row['confirmed']:
            msg = "You're already confirmed!"
        else:
            db.execute(
                "UPDATE subscribers SET confirmed=1, confirmed_at=? WHERE token=?",
                (datetime.utcnow().isoformat(), token)
            )
            db.commit()
            msg = "✓ You're confirmed! We'll email you when Groundwork updates."
    content = f"""
<div style="font-family:Inter,sans-serif;max-width:500px;margin:100px auto;text-align:center;padding:24px">
  <div style="font-size:48px;margin-bottom:16px">✓</div>
  <h2 style="color:#2d6a4f;margin-bottom:12px">{msg}</h2>
  <p style="color:#666;margin-bottom:24px">You'll hear from us when something worth knowing ships.</p>
  <a href="/" style="display:inline-block;padding:12px 24px;background:#2d6a4f;
     color:#fff;border-radius:8px;font-weight:600;text-decoration:none">← Back to Groundwork</a>
</div>"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Confirmed',
        description='Your Groundwork updates subscription is confirmed.',
        canonical=SITE_URL + '/signup'
    )

# ── Unsubscribe ───────────────────────────────────────────────────────────────
@app.route('/unsubscribe/<token>')
def unsubscribe(token):
    with get_db() as db:
        db.execute('DELETE FROM subscribers WHERE token=?', (token,))
        db.commit()
    content = """
<div style="font-family:Inter,sans-serif;max-width:500px;margin:100px auto;text-align:center;padding:24px">
  <h2 style="margin-bottom:12px">Unsubscribed</h2>
  <p style="color:#666">You've been removed from the list. No more emails from us.</p>
</div>"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Unsubscribed',
        description='You have been unsubscribed from Groundwork updates.',
        canonical=SITE_URL + '/signup'
    )

# ── Admin login ───────────────────────────────────────────────────────────────
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST' and 'password' in request.form:
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin')
        return redirect('/admin?err=1')

    if not session.get('admin'):
        err = request.args.get('err')
        return f"""
<div style="font-family:Inter,sans-serif;max-width:400px;margin:100px auto;padding:24px">
  <h2 style="margin-bottom:20px">Admin Login</h2>
  {'<p style="color:red;margin-bottom:12px">Wrong password.</p>' if err else ''}
  <form method="POST">
    <input name="password" type="password" placeholder="Admin password"
      style="width:100%;padding:10px 14px;border:1px solid #ddd;border-radius:8px;
             font-size:14px;margin-bottom:12px">
    <button type="submit"
      style="width:100%;padding:12px;background:#2d6a4f;color:#fff;border:none;
             border-radius:8px;font-size:14px;cursor:pointer">Log in</button>
  </form>
</div>"""

    with get_db() as db:
        total     = db.execute('SELECT COUNT(*) FROM subscribers').fetchone()[0]
        confirmed = db.execute('SELECT COUNT(*) FROM subscribers WHERE confirmed=1').fetchone()[0]
        recent    = db.execute(
            'SELECT email, name, confirmed, created_at FROM subscribers ORDER BY id DESC LIMIT 20'
        ).fetchall()
        past      = db.execute(
            'SELECT subject, sent_count, sent_at FROM emails_sent ORDER BY id DESC LIMIT 10'
        ).fetchall()

        # ── Analytics ──────────────────────────────────────────────────────────
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        views_total = db.execute('SELECT COALESCE(SUM(count),0) FROM page_views').fetchone()[0]
        views_week  = db.execute(
            'SELECT COALESCE(SUM(count),0) FROM page_views WHERE day >= ?', (week_ago,)
        ).fetchone()[0]
        dl_total    = db.execute('SELECT COALESCE(SUM(count),0) FROM downloads').fetchone()[0]
        dl_by_os    = db.execute(
            'SELECT platform, COALESCE(SUM(count),0) AS total, '
            '       COALESCE(SUM(CASE WHEN day >= ? THEN count ELSE 0 END),0) AS wk '
            'FROM downloads GROUP BY platform ORDER BY total DESC', (week_ago,)
        ).fetchall()
        top_pages   = db.execute(
            'SELECT path, SUM(count) AS total FROM page_views '
            'GROUP BY path ORDER BY total DESC LIMIT 12'
        ).fetchall()
        daily       = db.execute(
            'SELECT day, SUM(count) AS total FROM page_views '
            'WHERE day >= ? GROUP BY day ORDER BY day DESC', (week_ago,)
        ).fetchall()

    rows = ''.join(
        f"<tr><td style='padding:8px 12px'>{h(r['email'])}</td>"
        f"<td>{h(r['name'] or '')}</td>"
        f"<td>{'✓' if r['confirmed'] else '⏳'}</td>"
        f"<td style='color:#999;font-size:12px'>{r['created_at'][:10]}</td></tr>"
        for r in recent
    )
    past_rows = ''.join(
        f"<tr><td style='padding:8px 12px'>{h(p['subject'])}</td>"
        f"<td>{p['sent_count']}</td>"
        f"<td style='color:#999;font-size:12px'>{p['sent_at'][:10]}</td></tr>"
        for p in past
    ) or "<tr><td colspan='3' style='padding:12px;color:#999'>No emails sent yet</td></tr>"

    _OS_LABEL = {'windows': '🪟 Windows', 'windows-offline': '🪟 Windows (offline)',
                 'macos': '🍎 macOS', 'linux': '🐧 Linux'}
    dl_rows = ''.join(
        f"<tr><td style='padding:8px 12px'>{_OS_LABEL.get(d['platform'], h(d['platform']))}</td>"
        f"<td>{d['total']}</td>"
        f"<td style='color:#666'>{d['wk']}</td></tr>"
        for d in dl_by_os
    ) or "<tr><td colspan='3' style='padding:12px;color:#999'>No downloads counted yet</td></tr>"

    page_rows = ''.join(
        f"<tr><td style='padding:8px 12px'>{h(p['path'])}</td><td>{p['total']}</td></tr>"
        for p in top_pages
    ) or "<tr><td colspan='2' style='padding:12px;color:#999'>No page views counted yet</td></tr>"

    daily_rows = ''.join(
        f"<tr><td style='padding:8px 12px;color:#999;font-size:12px'>{d['day']}</td>"
        f"<td>{d['total']}</td></tr>"
        for d in daily
    ) or "<tr><td colspan='2' style='padding:12px;color:#999'>No views in the last 7 days</td></tr>"

    return f"""
<!DOCTYPE html><html><head>
<title>Groundwork Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* {{box-sizing:border-box;margin:0;padding:0}}
body {{font-family:Inter,sans-serif;background:#f5f5f0;padding:32px}}
.card {{background:#fff;border:1px solid #e0e0d8;border-radius:12px;padding:28px;margin-bottom:24px}}
h1 {{font-size:24px;font-weight:800;margin-bottom:24px}}
h2 {{font-size:18px;font-weight:700;margin-bottom:16px}}
.stats {{display:flex;gap:16px;margin-bottom:24px}}
.stat {{background:#f5f5f0;border-radius:8px;padding:16px 20px;flex:1}}
.stat .n {{font-size:32px;font-weight:800;color:#2d6a4f}}
.stat .l {{font-size:12px;color:#666;margin-top:2px}}
.field {{margin-bottom:16px}}
.field label {{display:block;font-size:13px;font-weight:600;margin-bottom:6px}}
.field input,.field textarea {{width:100%;padding:10px 14px;border:1px solid #e0e0d8;
  border-radius:8px;font-size:14px;font-family:inherit}}
.field textarea {{min-height:160px;resize:vertical}}
table {{width:100%;border-collapse:collapse;font-size:14px}}
th {{text-align:left;padding:8px 12px;border-bottom:2px solid #e0e0d8;
     font-size:12px;font-weight:600;color:#666;text-transform:uppercase}}
tr:hover {{background:#f9f9f7}}
.btn {{display:inline-block;padding:12px 24px;background:#2d6a4f;color:#fff;
       border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}}
.btn:hover {{opacity:.88}}
.msg {{margin-top:12px;font-size:14px;min-height:20px;color:#2d6a4f}}
</style></head><body>
<h1>Groundwork Admin</h1>

<div class="stats">
  <div class="stat"><div class="n">{total}</div><div class="l">Total signups</div></div>
  <div class="stat"><div class="n">{confirmed}</div><div class="l">Confirmed</div></div>
  <div class="stat"><div class="n">{total - confirmed}</div><div class="l">Unconfirmed</div></div>
</div>

<div class="stats">
  <div class="stat"><div class="n">{views_week}</div><div class="l">Page views (7 days)</div></div>
  <div class="stat"><div class="n">{views_total}</div><div class="l">Page views (all time)</div></div>
  <div class="stat"><div class="n">{dl_total}</div><div class="l">Downloads (all time)</div></div>
</div>

<div class="card">
  <h2>Downloads by operating system</h2>
  <table>
    <tr><th>Platform</th><th>All time</th><th>Last 7 days</th></tr>
    {dl_rows}
  </table>
</div>

<div class="card">
  <h2>Traffic</h2>
  <div style="display:flex;gap:24px;flex-wrap:wrap">
    <div style="flex:2;min-width:280px">
      <h3 style="font-size:13px;color:#666;text-transform:uppercase;margin-bottom:10px">Top pages (all time)</h3>
      <table>
        <tr><th>Page</th><th>Views</th></tr>
        {page_rows}
      </table>
    </div>
    <div style="flex:1;min-width:200px">
      <h3 style="font-size:13px;color:#666;text-transform:uppercase;margin-bottom:10px">Views per day (last 7)</h3>
      <table>
        <tr><th>Day</th><th>Views</th></tr>
        {daily_rows}
      </table>
    </div>
  </div>
  <p style="margin-top:16px;font-size:12px;color:#999">
    Aggregate counts only — no IP addresses, cookies, user agents, or personal data are stored.
    Known bots and static assets are excluded.
  </p>
</div>

<div class="card">
  <h2>Send Newsletter</h2>
  <div class="field">
    <label>Subject line</label>
    <input type="text" id="subj" placeholder="Groundwork update — June 2026">
  </div>
  <div class="field">
    <label>Message (plain text — will be formatted nicely in the email)</label>
    <textarea id="body" placeholder="Hi everyone,&#10;&#10;Here's what's new in Groundwork..."></textarea>
  </div>
  <button class="btn" onclick="sendNewsletter()">Send to {confirmed} confirmed subscribers →</button>
  <div class="msg" id="send-msg"></div>
</div>

<div class="card">
  <h2>Recent signups</h2>
  <table>
    <tr><th>Email</th><th>Name</th><th>Confirmed</th><th>Signed up</th></tr>
    {rows}
  </table>
</div>

<div class="card">
  <h2>Past emails sent</h2>
  <table>
    <tr><th>Subject</th><th>Recipients</th><th>Sent</th></tr>
    {past_rows}
  </table>
</div>

<script>
async function sendNewsletter() {{
  const subj = document.getElementById('subj').value.trim();
  const body = document.getElementById('body').value.trim();
  const msg  = document.getElementById('send-msg');
  if (!subj || !body) {{ msg.textContent = 'Fill in both fields.'; return; }}
  if (!confirm(`Send to {confirmed} subscribers?`)) return;
  msg.textContent = 'Sending…';
  const r = await fetch('/admin/send', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{subject: subj, body}}),
  }});
  const d = await r.json();
  msg.textContent = d.message;
}}
</script>
</body></html>"""

# ── Admin send newsletter ─────────────────────────────────────────────────────
@app.route('/admin/send', methods=['POST'])
def admin_send():
    if not session.get('admin'):
        abort(403)
    data    = request.get_json() or {}
    subject = data.get('subject', '').strip()
    body    = data.get('body', '').strip()
    if not subject or not body:
        return jsonify({'message': 'Missing subject or body.'})

    with get_db() as db:
        subs = db.execute(
            'SELECT email, name, token FROM subscribers WHERE confirmed=1'
        ).fetchall()

    sent = 0
    for sub in subs:
        unsub_url = f"{SITE_URL}/unsubscribe/{sub['token']}"
        html = f"""
<div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;padding:40px 20px">
  <h2 style="color:#1a1a2e;font-size:20px;margin-bottom:4px">Groundwork</h2>
  <hr style="border:none;border-top:1px solid #e0e0d8;margin-bottom:24px">
  <div style="color:#333;line-height:1.8;font-size:15px">
    {''.join(f'<p style="margin-bottom:14px">{p}</p>' for p in body.split('\n\n') if p.strip())}
  </div>
  <hr style="border:none;border-top:1px solid #e0e0d8;margin:32px 0 16px">
  <p style="color:#999;font-size:12px">
    You're receiving this because you signed up at groundworkfinance.app.<br>
    <a href="{unsub_url}" style="color:#999">Unsubscribe</a>
  </p>
</div>"""
        if send_email(sub['email'], sub['name'] or '', subject, html):
            sent += 1

    with get_db() as db:
        db.execute(
            'INSERT INTO emails_sent (subject, body, sent_count) VALUES (?,?,?)',
            (subject, body, sent)
        )
        db.commit()

    return jsonify({'message': f'✓ Sent to {sent} subscribers.'})

if __name__ == '__main__':
    app.run(debug=True)
