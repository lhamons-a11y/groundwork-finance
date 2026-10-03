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
  --ink:    #1a1a2e;
  --pine:   #2d6a4f;
  --gold:   #e9c46a;
  --ember:  #e76f51;
  --paper:  #fafaf7;
  --mist:   #f0f0eb;
  --steel:  #e0e0d8;
  --slate:  #666;
  --r:      8px;
}
body { font-family: 'Inter', sans-serif; background: var(--paper); color: var(--ink); line-height: 1.6; }
a { color: var(--pine); text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
.btn {
  display: inline-block; padding: 14px 28px; border-radius: var(--r);
  font-weight: 600; font-size: 15px; cursor: pointer; border: none;
  transition: opacity .15s;
}
.btn:hover { opacity: .88; text-decoration: none; }
.btn-primary { background: var(--pine); color: #fff; }
.btn-ghost { background: transparent; color: var(--pine); border: 2px solid var(--pine); }
.btn-gold { background: var(--gold); color: var(--ink); }

/* Nav — scoped to .site-nav; a bare `nav` selector also hit the KB sidebar
   (<nav class="kb-nav">), giving it a dark background under dark link text. */
.site-nav { background: var(--ink); padding: 0 24px; position: sticky; top: 0; z-index: 100; }
.nav-inner { max-width: 1100px; margin: 0 auto; display: flex; align-items: center;
             justify-content: space-between; height: 64px; }
.nav-logo { color: #fff; font-size: 20px; font-weight: 700; letter-spacing: -.5px; }
.nav-logo span { color: var(--gold); }
.nav-links { display: flex; gap: 32px; }
.nav-links a { color: rgba(255,255,255,.8); font-size: 14px; font-weight: 500; }
.nav-links a:hover { color: #fff; text-decoration: none; }
.nav-cta { background: var(--gold); color: var(--ink) !important;
           padding: 8px 18px; border-radius: var(--r); font-weight: 600 !important; }

/* Hero */
.hero { background: var(--ink); color: #fff; padding: 100px 24px 80px; text-align: center; }
.beta-badge {
  display: inline-block; background: var(--gold); color: var(--ink);
  font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
  padding: 4px 12px; border-radius: 20px; margin-bottom: 24px;
}
.hero h1 { font-size: clamp(32px, 5vw, 60px); font-weight: 800; line-height: 1.15;
           letter-spacing: -.5px; margin-bottom: 20px; max-width: 800px; margin-inline: auto; }
.hero h1 em { color: var(--gold); font-style: normal; }
.hero p { font-size: 18px; color: rgba(255,255,255,.75); max-width: 560px;
          margin: 0 auto 40px; }
.hero-btns { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }

/* Beta banner */
.beta-bar { background: #fff3cd; border-bottom: 1px solid #ffc107;
            padding: 12px 24px; text-align: center; font-size: 14px; color: #856404; }

/* Features */
.features { padding: 80px 24px; }
.section-label { font-size: 12px; font-weight: 700; letter-spacing: .12em;
                 text-transform: uppercase; color: var(--pine); margin-bottom: 12px; }
.section-title { font-size: clamp(24px, 4vw, 42px); font-weight: 800;
                 letter-spacing: -.5px; margin-bottom: 16px; }
.section-sub { font-size: 17px; color: var(--slate); max-width: 560px; }
.features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                 gap: 24px; margin-top: 56px; }
.feature-card { background: #fff; border: 1px solid var(--steel); border-radius: 12px;
                padding: 28px; transition: box-shadow .2s; }
.feature-card:hover { box-shadow: 0 8px 32px rgba(0,0,0,.08); }
.feature-icon { font-size: 32px; margin-bottom: 16px; }
.feature-card h3 { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.feature-card p { font-size: 14px; color: var(--slate); line-height: 1.7; }

/* Screenshots */
.screenshots { background: var(--mist); padding: 80px 24px; }
.screenshot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                   gap: 20px; margin-top: 48px; }
.screenshot-item { background: var(--ink); border-radius: 12px; overflow: hidden;
                   aspect-ratio: 16/10; display: flex; align-items: center;
                   justify-content: center; position: relative; }
.screenshot-mock { width: 100%; height: 100%; padding: 16px; }
.mock-bar { height: 28px; background: rgba(255,255,255,.05); border-radius: 6px 6px 0 0;
            display: flex; align-items: center; padding: 0 12px; gap: 6px; margin-bottom: 8px; }
.mock-dot { width: 8px; height: 8px; border-radius: 50%; }
.mock-content { display: flex; flex-direction: column; gap: 8px; }
.mock-row { height: 8px; background: rgba(255,255,255,.1); border-radius: 4px; }
.mock-card { background: rgba(255,255,255,.05); border-radius: 6px; padding: 10px;
             border: 1px solid rgba(255,255,255,.08); }
.mock-num { font-family: 'DM Mono', monospace; font-size: 18px; font-weight: 600; color: var(--gold); }
.mock-lbl { font-size: 10px; color: rgba(255,255,255,.4); margin-bottom: 4px; }
.mock-bar-chart { display: flex; align-items: flex-end; gap: 4px; height: 40px; margin-top: 8px; }
.mock-bar-item { flex: 1; background: var(--pine); border-radius: 2px 2px 0 0; opacity: .7; }
.screenshot-label { text-align: center; margin-top: 12px; font-size: 13px;
                    font-weight: 600; color: var(--ink); }

/* Mission */
.mission { padding: 80px 24px; display: grid;
           grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; }
.mission-text h2 { font-size: clamp(24px, 3vw, 36px); font-weight: 800; margin-bottom: 20px; }
.mission-text p { color: var(--slate); line-height: 1.8; margin-bottom: 16px; }
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.stat-card { background: var(--ink); color: #fff; padding: 24px; border-radius: 12px; }
.stat-num { font-size: 36px; font-weight: 800; color: var(--gold); }
.stat-lbl { font-size: 13px; color: rgba(255,255,255,.6); margin-top: 4px; }

/* Signup */
.signup-section { background: var(--pine); padding: 80px 24px; text-align: center; color: #fff; }
.signup-section h2 { font-size: clamp(24px, 4vw, 40px); font-weight: 800; margin-bottom: 12px; }
.signup-section p { color: rgba(255,255,255,.8); margin-bottom: 32px; font-size: 16px; }
.signup-form { display: flex; gap: 12px; max-width: 500px; margin: 0 auto; flex-wrap: wrap; }
.signup-form input {
  flex: 1; min-width: 200px; padding: 14px 18px; border-radius: var(--r);
  border: none; font-size: 15px; font-family: inherit;
}
.signup-form .btn { background: var(--gold); color: var(--ink); }
.signup-msg { margin-top: 16px; font-size: 14px; min-height: 20px; }

/* Footer */
footer { background: var(--ink); color: rgba(255,255,255,.5); padding: 48px 24px;
         text-align: center; font-size: 13px; }
footer a { color: rgba(255,255,255,.6); }
.footer-links { display: flex; justify-content: center; gap: 24px; margin-bottom: 20px; flex-wrap: wrap; }

/* Download page */
.download-hero { background: var(--ink); color: #fff; padding: 80px 24px; text-align: center; }
.download-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                 gap: 24px; margin-top: 48px; padding: 60px 24px; }
.download-card { background: #fff; border: 2px solid var(--steel); border-radius: 12px;
                 padding: 32px; text-align: center; transition: border-color .2s; }
.download-card:hover { border-color: var(--pine); }
.download-card .os-icon { font-size: 48px; margin-bottom: 16px; }
.download-card h3 { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
.download-card p { color: var(--slate); font-size: 14px; margin-bottom: 24px; }
.requirements { background: var(--mist); border-radius: var(--r); padding: 16px;
                font-size: 13px; color: var(--slate); margin-top: 16px; text-align: left; }

/* KB */
.kb-grid { display: grid; grid-template-columns: 240px 1fr; gap: 40px;
           padding: 60px 24px; max-width: 1100px; margin: 0 auto; }
.kb-nav { position: sticky; top: 84px; align-self: start; }
.kb-nav h3 { font-size: 12px; font-weight: 700; letter-spacing: .1em;
             text-transform: uppercase; color: var(--slate); margin-bottom: 12px; }
.kb-nav a { display: block; padding: 8px 12px; border-radius: 6px; font-size: 14px;
            color: var(--ink); margin-bottom: 2px; }
.kb-nav a:hover, .kb-nav a.active { background: var(--mist); text-decoration: none; }
.kb-content h1 { font-size: 32px; font-weight: 800; margin-bottom: 8px; }
.kb-content .kb-sub { color: var(--slate); margin-bottom: 40px; }
.kb-article { margin-bottom: 48px; padding-bottom: 48px; border-bottom: 1px solid var(--steel); }
.kb-article h2 { font-size: 22px; font-weight: 700; margin-bottom: 12px; color: var(--ink); }
.kb-article h3 { font-size: 16px; font-weight: 600; margin: 20px 0 8px; }
.kb-article p { color: var(--slate); line-height: 1.8; margin-bottom: 12px; }
.kb-article ul { color: var(--slate); padding-left: 20px; line-height: 2; }
.kb-tip { background: #e8f5e9; border-left: 3px solid var(--pine); padding: 12px 16px;
          border-radius: 0 6px 6px 0; font-size: 14px; margin: 16px 0; }

/* Admin */
.admin-wrap { max-width: 700px; margin: 60px auto; padding: 0 24px; }
.admin-card { background: #fff; border: 1px solid var(--steel); border-radius: 12px; padding: 32px; }
.field { margin-bottom: 20px; }
.field label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.field input, .field textarea {
  width: 100%; padding: 10px 14px; border: 1px solid var(--steel);
  border-radius: var(--r); font-size: 14px; font-family: inherit;
}
.field textarea { min-height: 200px; resize: vertical; }
.stats-row { display: flex; gap: 20px; margin-bottom: 24px; }
.stat-pill { background: var(--mist); border-radius: var(--r); padding: 16px 20px; flex: 1; }
.stat-pill .n { font-size: 28px; font-weight: 800; color: var(--pine); }
.stat-pill .l { font-size: 12px; color: var(--slate); }

@media (max-width: 768px) {
  .mission { grid-template-columns: 1fr; gap: 40px; }
  .kb-grid { grid-template-columns: 1fr; }
  .kb-nav { position: static; }
  .nav-links { display: none; }
}
"""

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} — Groundwork</title>
  <meta name="description" content="{{ description }}">
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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>""" + SITE_CSS + """</style>
</head>
<body>

<div class="beta-bar">
  🎉 <strong>Groundwork 1.1 is here</strong> — free to download and use.
  <a href="/download">Get the latest version</a>.
</div>

<nav class="site-nav">
  <div class="nav-inner">
    <a href="/" class="nav-logo">Ground<span>work</span></a>
    <div class="nav-links">
      <a href="/features">Features</a>
      <a href="/download">Download</a>
      <a href="/knowledge-base">Help</a>
      <a href="/about">About</a>
      <a href="/download" class="nav-cta">Download Free</a>
    </div>
  </div>
</nav>

{% block content %}{% endblock %}

<footer>
  <div class="footer-links">
    <a href="/">Home</a>
    <a href="/features">Features</a>
    <a href="/download">Download</a>
    <a href="/knowledge-base">Knowledge Base</a>
    <a href="/changelog">Changelog</a>
    <a href="/about">About</a>
    <a href="/privacy">Privacy</a>
    <a href="/terms">Terms</a>
  </div>
  <p>© 2026 Groundwork · Free personal finance software · Your data stays on your machine</p>
  <p style="margin-top:8px">Questions? <a href="mailto:hello@groundworkfinance.app">hello@groundworkfinance.app</a></p>
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
    'description': 'Free personal finance app for budgeting, debt payoff, and net worth tracking. '
                   'No account, no subscription — your data stays on your machine.',
    'url': SITE_URL,
    'downloadUrl': SITE_URL + '/download',
    'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'},
}) + '</script>'


@app.route('/')
def home():
    return render_template_string(BASE_TEMPLATE.replace(
        '{% block content %}{% endblock %}', HOME_CONTENT
    ), title='Stop living paycheck to paycheck',
       description='Groundwork is a free personal finance app that helps you stop living paycheck to paycheck and build a real plan to get out of debt.',
       canonical=SITE_URL + '/',
       structured_data=_HOME_STRUCTURED_DATA)

HOME_CONTENT = """
<section class="hero">
  <div class="beta-badge">Version 1.1 — Free Download</div>
  <h1>Stop living <em>paycheck to paycheck.</em><br>Groundwork gives you a real plan.</h1>
  <p>A free personal finance app that shows exactly where your money goes and builds a step-by-step path out of debt — no subscription, no cloud, no nonsense.</p>
  <div class="hero-btns">
    <a href="/download" class="btn btn-primary" style="font-size:17px;padding:16px 36px">
      ⬇ Download Free for <span class="os-download-label">Windows</span>
    </a>
    <a href="/features" class="btn btn-ghost" style="color:#fff;border-color:rgba(255,255,255,.4)">
      See what it does →
    </a>
  </div>
</section>

<section class="behavior-focus" style="background: var(--mist); padding: 80px 24px; text-align: center;">
  <div class="container">
    <div class="section-label">Why Groundwork is Different</div>
    <h2 class="section-title" style="margin-bottom: 48px;">Groundwork learns from your actual behavior, not your perfect plan.</h2>

    <div style="max-width: 720px; margin: 0 auto; text-align: left; line-height: 1.8; color: var(--slate); font-size: 16px;">
      <p style="margin-bottom: 20px;">
        Most finance apps assume you'll follow their budget perfectly. <strong>Groundwork assumes you won't—because people don't.</strong>
      </p>

      <p style="margin-bottom: 20px;">
        Instead, it watches what you actually do (when you pay, how you adjust budgets, how quickly you recover from mistakes), learns the patterns, and adapts. It rewards progress, not perfection.
      </p>

      <p>
        <strong>The goal isn't to optimize your money.</strong> It's to help you become the kind of person who naturally makes good financial decisions.
      </p>
    </div>
  </div>
</section>

<section class="features">
  <div class="container">
    <div class="section-label">What Groundwork does</div>
    <h2 class="section-title">Everything you need to get out of debt</h2>
    <p class="section-sub">Built for real people who are tired of not knowing where their money went.</p>
    <div class="features-grid">
      <div class="feature-card">
        <div class="feature-icon">📊</div>
        <h3>Budget that actually works</h3>
        <p>Import your bank transactions and see exactly where every dollar went. No manual entry, no spreadsheets.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">💳</div>
        <h3>Debt payoff planner</h3>
        <p>Snowball or avalanche — Groundwork builds your payoff schedule and shows your debt-free date.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📈</div>
        <h3>Net worth tracker</h3>
        <p>Watch your number go up every month. Balances update automatically as your transactions import.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🎁</div>
        <h3>Gift & seasonal budgeting</h3>
        <p>Never get caught off guard by Christmas or birthdays again. Plan ahead with sinking funds.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">✦</div>
        <h3>AI monthly report</h3>
        <p>Plain-English summary of how your month went and one concrete thing to do differently — runs privately on your own machine by default.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🔒</div>
        <h3>Your data stays on your machine</h3>
        <p>No account needed. No cloud sync. No subscription. Your finances are nobody else's business.</p>
      </div>
    </div>
  </div>
</section>

<section class="screenshots">
  <div class="container">
    <div class="section-label">See it in action</div>
    <h2 class="section-title">Built for clarity, not complexity</h2>
    <div class="screenshot-grid">
      <div>
        <div class="screenshot-item">
          <div class="screenshot-mock">
            <div class="mock-bar">
              <div class="mock-dot" style="background:#e76f51"></div>
              <div class="mock-dot" style="background:#e9c46a"></div>
              <div class="mock-dot" style="background:#2d6a4f"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
              <div class="mock-card">
                <div class="mock-lbl">Monthly Income</div>
                <div class="mock-num">$4,200</div>
              </div>
              <div class="mock-card">
                <div class="mock-lbl">Spent So Far</div>
                <div class="mock-num" style="color:#e76f51">$3,180</div>
              </div>
            </div>
            <div class="mock-card">
              <div class="mock-lbl">Left to spend</div>
              <div class="mock-num" style="color:#2d6a4f">$1,020</div>
              <div class="mock-bar-chart">
                <div class="mock-bar-item" style="height:80%"></div>
                <div class="mock-bar-item" style="height:45%"></div>
                <div class="mock-bar-item" style="height:65%"></div>
                <div class="mock-bar-item" style="height:30%"></div>
                <div class="mock-bar-item" style="height:90%"></div>
                <div class="mock-bar-item" style="height:55%"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="screenshot-label">Dashboard — your money at a glance</div>
      </div>
      <div>
        <div class="screenshot-item">
          <div class="screenshot-mock">
            <div class="mock-bar">
              <div class="mock-dot" style="background:#e76f51"></div>
              <div class="mock-dot" style="background:#e9c46a"></div>
              <div class="mock-dot" style="background:#2d6a4f"></div>
            </div>
            <div class="mock-content">
              <div class="mock-card" style="border-left:3px solid #e76f51">
                <div class="mock-lbl">Credit Card A · 19.9% APR</div>
                <div class="mock-num">$3,400</div>
                <div style="height:4px;background:rgba(255,255,255,.1);border-radius:2px;margin-top:6px">
                  <div style="width:68%;height:100%;background:#e76f51;border-radius:2px"></div>
                </div>
              </div>
              <div class="mock-card" style="border-left:3px solid #e9c46a">
                <div class="mock-lbl">Car Loan · 6.9% APR</div>
                <div class="mock-num">$8,200</div>
                <div style="height:4px;background:rgba(255,255,255,.1);border-radius:2px;margin-top:6px">
                  <div style="width:40%;height:100%;background:#e9c46a;border-radius:2px"></div>
                </div>
              </div>
              <div class="mock-card">
                <div class="mock-lbl">Debt-free date</div>
                <div class="mock-num" style="color:#2d6a4f;font-size:14px">March 2027 ✓</div>
              </div>
            </div>
          </div>
        </div>
        <div class="screenshot-label">Debt page — snowball or avalanche</div>
      </div>
      <div>
        <div class="screenshot-item">
          <div class="screenshot-mock">
            <div class="mock-bar">
              <div class="mock-dot" style="background:#e76f51"></div>
              <div class="mock-dot" style="background:#e9c46a"></div>
              <div class="mock-dot" style="background:#2d6a4f"></div>
            </div>
            <div class="mock-content">
              <div style="color:rgba(255,255,255,.4);font-size:10px;margin-bottom:4px">NET WORTH</div>
              <div class="mock-num" style="font-size:28px;margin-bottom:8px">$12,450</div>
              <div style="display:flex;align-items:flex-end;gap:3px;height:50px">
                <div style="flex:1;background:var(--pine);opacity:.5;height:30%;border-radius:2px 2px 0 0"></div>
                <div style="flex:1;background:var(--pine);opacity:.6;height:45%;border-radius:2px 2px 0 0"></div>
                <div style="flex:1;background:var(--pine);opacity:.7;height:55%;border-radius:2px 2px 0 0"></div>
                <div style="flex:1;background:var(--pine);opacity:.8;height:70%;border-radius:2px 2px 0 0"></div>
                <div style="flex:1;background:var(--pine);opacity:.9;height:85%;border-radius:2px 2px 0 0"></div>
                <div style="flex:1;background:var(--gold);height:100%;border-radius:2px 2px 0 0"></div>
              </div>
              <div style="color:rgba(255,255,255,.4);font-size:10px;margin-top:4px">6-month trend ↑ 34%</div>
            </div>
          </div>
        </div>
        <div class="screenshot-label">Net worth — watch it grow</div>
      </div>
    </div>
  </div>
</section>

<section class="mission container">
  <div class="mission-text">
    <div class="section-label">Why Groundwork exists</div>
    <h2>Built for people who are tired of being broke</h2>
    <p>Most personal finance apps are built for people who already have money. They're beautiful, expensive, and completely useless if you're trying to figure out how to make rent and pay off $12,000 in credit card debt at the same time.</p>
    <p>Groundwork is different. It was built by someone who's been there — who knows that what you need isn't another budgeting philosophy, but a concrete plan with real numbers and a real date when things get better.</p>
    <p>It's free. Always will be.</p>
    <a href="/about" class="btn btn-ghost" style="margin-top:8px">Our story →</a>
  </div>
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-num">78%</div>
      <div class="stat-lbl">of Americans live paycheck to paycheck</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">$0</div>
      <div class="stat-lbl">Cost of Groundwork. Free forever.</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">100%</div>
      <div class="stat-lbl">of your data stays on your machine</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">1 app</div>
      <div class="stat-lbl">Budget · Debt · Net worth · Reports</div>
    </div>
  </div>
</section>

<section class="signup-section">
  <div class="container">
    <h2>Get notified when we update</h2>
    <p>New features ship regularly. Drop your email and we'll let you know.</p>
    <div class="signup-form">
      <input type="text" id="signup-name" placeholder="Your name" style="max-width:160px">
      <input type="email" id="signup-email" placeholder="Your email address">
      <button class="btn" onclick="submitSignup()">Notify me →</button>
    </div>
    <div class="signup-msg" id="signup-msg"></div>
    <p style="margin-top:16px;font-size:12px;color:rgba(255,255,255,.5)">
      No spam. We send one email when something worth knowing ships.
    </p>
  </div>
</section>

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
<section class="download-hero">
  <h1 style="font-size:clamp(28px,4vw,48px);font-weight:800;margin-bottom:12px">
    Download Groundwork
  </h1>
  <p style="color:rgba(255,255,255,.7);font-size:16px">
    Free. No account. No subscription. Your data stays on your machine.
  </p>
  <div class="beta-badge" style="margin-top:20px">Version 1.1 — Now available</div>
</section>

<p class="container" style="font-size:14px;color:var(--slate, #64748b);line-height:1.6;margin-bottom:16px">
  <strong>Use a system that still gets security updates.</strong> Groundwork holds your financial data, and an
  up-to-date operating system is the first thing protecting it - so we suggest running it on one that is still
  supported. Groundwork doesn't refuse an older system: on an older computer that stays offline, that's perfectly fine.
</p>
<div class="download-grid container">
  <div class="download-card">
    <div class="os-icon">🪟</div>
    <h3>Windows</h3>
    <p>Windows 11 suggested. Double-click the installer and you're done in 60 seconds.</p>
    <a href="/dl/windows" class="btn btn-primary" style="width:100%;text-align:center">
      ⬇ Download for Windows
    </a>
    <div class="requirements">
      <strong>Requirements:</strong><br>
      Windows 11 (64-bit) suggested; Windows 10 still works<br>
      Microsoft Edge WebView2 (usually already installed)<br>
      ~2.5GB disk space (includes the built-in local AI model)<br>
      4GB RAM (8GB+ for the optional local AI)
    </div>
    <div style="margin-top:12px;font-size:12px;color:var(--slate)">
      Local AI sets itself up automatically from Settings — but if you'd
      rather have it all bundled in from the start (or expect to be
      offline for that first setup), grab the
      <a href="/dl/windows-offline">offline installer</a>
      instead (~3.3GB, includes Ollama and a local model — nothing to
      download later).
    </div>
  </div>

  <div class="download-card">
    <div class="os-icon">🍎</div>
    <h3>macOS</h3>
    <p>Apple Silicon and Intel Macs. Unzip and drag Groundwork into Applications.</p>
    <a href="/dl/macos" class="btn btn-primary" style="width:100%;text-align:center">
      ⬇ Download for macOS
    </a>
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
    <a href="/dl/linux" class="btn btn-primary" style="width:100%;text-align:center">
      ⬇ Download for Linux
    </a>
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

<div class="container" style="padding:40px 24px;text-align:center">
  <h3 style="margin-bottom:16px">Having trouble installing?</h3>
  <p style="color:var(--slate);margin-bottom:20px">
    Check the <a href="/knowledge-base#install">installation guide</a> or
    email <a href="mailto:support@groundworkfinance.app">support@groundworkfinance.app</a>
  </p>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Download',
        description='Download Groundwork free for Windows, macOS, or Linux. No account, no subscription — your financial data stays on your machine.',
        canonical=SITE_URL + '/download'
    )

# ── Knowledge Base ────────────────────────────────────────────────────────────
@app.route('/knowledge-base')
def knowledge_base():
    content = """
<div style="background:var(--ink);padding:48px 24px;color:#fff;text-align:center">
  <h1 style="font-size:36px;font-weight:800;margin-bottom:8px">Knowledge Base</h1>
  <p style="color:rgba(255,255,255,.7)">Everything you need to get started and get the most out of Groundwork</p>
</div>

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
    <p class="kb-sub">Groundwork is designed to be simple — but we've documented everything just in case.</p>

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
      <div class="kb-tip">💡 Groundwork remembers your categorization choices. The more you use it, the smarter it gets.</div>
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
      <p>The Report Center has ten built-in reports, several of which can include an AI-written narrative.</p>
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
      <p>Out of the box, Groundwork runs AI <strong>on your own machine</strong> using <a href="https://ollama.com" target="_blank">Ollama</a>. Nothing ever leaves your computer, there's no API key, and there's no cost. In <strong>Settings → AI</strong>, click <strong>Set up Local AI</strong> and Groundwork installs Ollama and a small language model for you (a few GB of disk space). Every other feature of Groundwork works fully whether or not you set this up.</p>
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
        <li>AI reports send aggregated numbers only — no names, no account details.</li>
        <li>Uninstalling Groundwork does not delete your data — it stays in AppData until you delete it yourself.</li>
      </ul>
    </div>

    <div class="kb-article" id="report-bug">
      <h2>Reporting a bug</h2>
      <p>Groundwork is actively maintained. If something breaks:</p>
      <p>1. In the app, click <strong>⚑ Report</strong> in the top bar.</p>
      <p>2. Describe what you were doing when it broke.</p>
      <p>3. Click <strong>Open in mail app</strong> — the report goes to support@groundworkfinance.app with your error log attached.</p>
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
<section class="hero" style="padding:80px 24px 60px">
  <h1 style="font-size:clamp(28px,4vw,48px)">About Groundwork</h1>
  <p>Why a free personal finance app exists — and who built it.</p>
</section>
<div class="container" style="max-width:700px;padding:60px 24px">
  <h2 style="font-size:28px;font-weight:800;margin-bottom:20px">The problem with most finance apps</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:16px">
    Most personal finance apps are built for people who already have money. They're beautiful, 
    expensive, and assume you have a surplus to manage. If you're living paycheck to paycheck 
    — trying to figure out how to pay off $8,000 in credit card debt while keeping the lights 
    on — they're not built for you.
  </p>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:16px">
    Groundwork was built from scratch for that situation. It started as a tool for one family 
    trying to get their finances under control — track spending, build a debt payoff plan, and 
    actually see a date when things would be different. It grew from there.
  </p>
  <h2 style="font-size:28px;font-weight:800;margin:40px 0 20px">Why it's free</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:16px">
    Because the people who need it most can't afford a subscription. Simple as that.
    Groundwork will always be free to download and use. Your data stays on your machine. 
    No account, no subscription, no ads.
  </p>
  <h2 style="font-size:28px;font-weight:800;margin:40px 0 20px">Feedback</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    Groundwork 1.1 is here and people are using it every day. It's actively maintained, and
    if something breaks, the ⚑ Report button in the app sends us the error log directly.
    We read every one.
  </p>
  <a href="/download" class="btn btn-primary">Download Groundwork free →</a>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='About',
        description='Groundwork is a free, privacy-first personal finance app built to help you get out of debt and stop living paycheck to paycheck.',
        canonical=SITE_URL + '/about'
    )

# ── Privacy page ──────────────────────────────────────────────────────────────
@app.route('/privacy')
def privacy():
    content = """
<div class="container" style="max-width:700px;padding:60px 24px">
  <h1 style="font-size:36px;font-weight:800;margin-bottom:8px">Privacy Policy</h1>
  <p style="color:var(--slate);margin-bottom:40px">Last updated: July 2026</p>
  <h2 style="font-size:20px;font-weight:700;margin-bottom:12px">Your data stays on your machine</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:20px">
    Groundwork is a desktop application. Your financial data — transactions, balances, 
    budgets, debt information — is stored in a SQLite database on your computer. 
    We have no access to it. It never leaves your machine unless you explicitly export it.
  </p>
  <h2 style="font-size:20px;font-weight:700;margin-bottom:12px">This website</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:20px">
    If you sign up for email updates on this website, we store your email address and name 
    to send you product updates. We use SendGrid to deliver emails. We never sell or share 
    your email address. You can unsubscribe at any time by emailing hello@groundworkfinance.app.
  </p>
  <h2 style="font-size:20px;font-weight:700;margin-bottom:12px">AI features</h2>
  <p style="color:var(--slate);line-height:1.9;margin-bottom:20px">
    Groundwork's AI features are optional and run <strong>only on your own machine</strong>: the
    app uses a language model on your computer (via Ollama), so nothing is sent to an AI service
    and no API key exists. There is no cloud AI option.
  </p>
  <h2 style="font-size:20px;font-weight:700;margin-bottom:12px">Contact</h2>
  <p style="color:var(--slate);line-height:1.9">
    Questions about privacy? Email <a href="mailto:hello@groundworkfinance.app">hello@groundworkfinance.app</a>
  </p>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Privacy Policy',
        description='Groundwork stores your financial data locally on your machine. No account, no cloud, no telemetry. Read our full privacy policy.',
        canonical=SITE_URL + '/privacy'
    )

# ── Terms of Use / EULA ───────────────────────────────────────────────────────
# Mirrors EULA.txt (the text shown in the installer and in-app). Keep the two
# in sync when either changes.
@app.route('/terms')
def terms():
    content = """
<div class="container" style="max-width:760px;padding:60px 24px">
  <h1 style="font-size:36px;font-weight:800;margin-bottom:4px">Terms of Use &amp; License</h1>
  <p style="color:var(--slate);margin-bottom:8px">End User License Agreement · Version 1.1 · Effective September 27, 2026</p>
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
  <p style="color:var(--slate);line-height:1.9;margin-bottom:24px">
    Your financial data is stored locally on your device. The publisher does not collect or
    receive it. See the <a href="/privacy">Privacy Policy</a> for details.
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
    content = """
<section class="hero" style="padding:80px 24px 60px">
  <h1 style="font-size:clamp(28px,4vw,48px)">Everything in Groundwork</h1>
  <p>One app. Every tool you need to get out of debt and start building wealth.</p>
</section>
<div class="features" style="padding-top:40px">
  <div class="container">
    <div class="features-grid">
      <div class="feature-card"><div class="feature-icon">📊</div><h3>Budget</h3>
        <p>Monthly income and expense tracking. See what you have left in real time as transactions import from your bank.</p></div>
      <div class="feature-card"><div class="feature-icon">💳</div><h3>Debt Tracker</h3>
        <p>Snowball or avalanche payoff plans. See your debt-free date and watch it get closer every month.</p></div>
      <div class="feature-card"><div class="feature-icon">📒</div><h3>Ledger</h3>
        <p>Full transaction history with auto-categorization, search, split transactions, and reconciliation.</p></div>
      <div class="feature-card"><div class="feature-icon">📈</div><h3>Net Worth</h3>
        <p>Track assets and liabilities over time. Your checking and savings balance automatically.</p></div>
      <div class="feature-card"><div class="feature-icon">🎁</div><h3>Gift Budget</h3>
        <p>Plan gifts for every person and occasion. Never get caught off guard by birthdays or Christmas again.</p></div>
      <div class="feature-card"><div class="feature-icon">✈️</div><h3>Trip Planner</h3>
        <p>Plan a vacation with a target budget and deadline. Groundwork builds the monthly savings plan automatically.</p></div>
      <div class="feature-card"><div class="feature-icon">🏦</div><h3>Investments</h3>
        <p>Track your portfolio holdings, cost basis, and performance. Import investment account transactions.</p></div>
      <div class="feature-card"><div class="feature-icon">📋</div><h3>Reports</h3>
        <p>Ten built-in reports, several with AI-written narratives. Print any report with one click.</p></div>
      <div class="feature-card"><div class="feature-icon">🛒</div><h3>Before You Buy</h3>
        <p>Evaluate a big purchase before committing. See exactly what it does to your budget and debt-free date.</p></div>
      <div class="feature-card"><div class="feature-icon">✦</div><h3>AI Analysis</h3>
        <p>Optional AI monthly report — runs on your own machine (no key, nothing sent out). Plain English, one concrete suggestion per month.</p></div>
      <div class="feature-card"><div class="feature-icon">🔒</div><h3>Private by design</h3>
        <p>Runs on your machine. No account. No cloud. No subscription. Your data is yours.</p></div>
      <div class="feature-card"><div class="feature-icon">💾</div><h3>Import from Quicken</h3>
        <p>QIF, QFX, OFX, and CSV import. Bring your history over from Quicken, Mint, or any bank export.</p></div>
    </div>
    <div style="text-align:center;margin-top:60px">
      <a href="/download" class="btn btn-primary" style="font-size:17px;padding:16px 36px">
        Download free for <span class="os-download-label">Windows</span> →
      </a>
    </div>
  </div>
</div>
"""
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Features',
        description='Budgeting, debt payoff, net worth tracking, gift planning, and more — see everything Groundwork does to help you take control of your money.',
        canonical=SITE_URL + '/features'
    )


# ── Signup page ───────────────────────────────────────────────────────────────
# Email-updates signup, linked from the footer and the signup form.
@app.route('/signup')
def signup():
    content = """
<section class="signup-section" style="min-height:60vh;display:flex;align-items:center">
  <div class="container">
    <h2>Get Groundwork updates</h2>
    <p>New features ship regularly. Drop your email and we'll let you know when something worth knowing ships.</p>
    <div class="signup-form">
      <input type="text" id="signup-name" placeholder="Your name" style="max-width:160px">
      <input type="email" id="signup-email" placeholder="Your email address">
      <button class="btn" onclick="submitSignup()">Notify me →</button>
    </div>
    <div class="signup-msg" id="signup-msg"></div>
    <p style="margin-top:16px;font-size:12px;color:rgba(255,255,255,.5)">
      No spam. One email when something ships. Unsubscribe anytime.
    </p>
  </div>
</section>

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
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content),
        title='Sign up for updates',
        description="Get notified about new Groundwork releases, including macOS and Linux availability. No spam, unsubscribe any time.",
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
  <h1 style="font-size:32px;font-weight:800;margin-bottom:8px">Changelog</h1>
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
