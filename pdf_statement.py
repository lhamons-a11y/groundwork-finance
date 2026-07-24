"""
pdf_statement.py — PDF credit-card statement extraction (GROUNDWORK_LLM_BUILD_PLAN
Phase 4). Issuer-agnostic: works from the statement's own printed text, not a
per-issuer template, so it isn't tied to any single card company's format.

Two-stage trust model, same principle as the voice gate (_voiceGateCheck in
app.js / voice_discipline_test.py):
  1. pdfplumber does layout -> text ONLY. It never interprets meaning.
  2. The model reads that raw text and returns strict JSON. Every number it
     writes is then checked against the raw text (R8-style number
     provenance) — a figure the model wrote but the statement never printed
     is nulled out (summary field) or dropped (transaction) rather than
     trusted. The engine sources numbers; the model never does.

server.py calls extract_text() + validate_and_clean() around its own AI-provider
call (_ai_complete_text) — kept out of this module so it stays a pure,
independently-testable pipeline with no Flask/DB dependency.
"""
import re
import json
import hashlib

ISSUER_GENERIC = 'credit_card'

# Mirrors _FIN_NUM_RE / _financial_numbers() in app.js and
# voice_discipline_test.py exactly — the same "what counts as a financial
# figure" definition everywhere in the codebase.
_FIN_NUM_RE = re.compile(r'\$\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?%')


def _financial_numbers(s: str) -> set:
    """Extract every dollar/percent figure in `s` and normalize to a bare
    numeric string (strip $, commas, spaces, trailing %)."""
    out = set()
    for m in _FIN_NUM_RE.findall(s or ''):
        norm = m.replace('$', '').replace(',', '').replace(' ', '').rstrip('%').strip()
        if norm:
            out.add(norm)
    return out


def _number_candidates(val) -> set:
    """A model-returned JSON number (e.g. 1234.5) won't textually match a
    page's printed "$1,234.50" unless we try a few plausible formattings.
    Returns every normalized string form worth checking against the page's
    extracted figures. Never invents a match — just tolerates formatting,
    including a payment/credit line the model signed negative even though
    the schema says amounts are always positive (the source regex doesn't
    capture a leading "-" before "$" either, so the page's own figure is
    unsigned) — direction is already carried by the separate type field."""
    try:
        f = abs(float(val))
    except (TypeError, ValueError):
        return {str(val).strip()}
    out = {f'{f:.2f}'}
    if f == int(f):
        out.add(str(int(f)))
    else:
        out.add(str(f))
    return out


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_text(pdf_bytes: bytes) -> str:
    """Layout -> text only, page by page. Raises ValueError on a PDF with no
    extractable text layer (e.g. a scanned image) so the caller can surface a
    clear, honest error instead of silently extracting nothing."""
    import io
    import pdfplumber
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or '')
    text = '\n\n'.join(pages).strip()
    if not text:
        raise ValueError(
            'No extractable text found in this PDF — it may be a scanned '
            'image without a text layer. Try a digital statement export instead.')
    return text


# A real multi-page statement is mostly legal boilerplate — billing-rights
# disclosures, interest-calculation methodology, dispute procedures — pages
# that can outweigh the actual account summary and transaction list by 5-10x.
# A small local model's limited context gets overwhelmed by that and drifts
# into summarizing the boilerplate instead of extracting data (confirmed on a
# real 3-page statement: a page of pure disclosure text made phi3.5 abandon
# the JSON extraction task entirely). This is a fully general, issuer-agnostic
# heuristic — not tied to any one card company's specific wording — since
# real account data is inherently numeric-dense and boilerplate prose is
# inherently numeric-sparse, regardless of issuer.
_BOILERPLATE_MIN_LEN     = 3000  # only ever drops LARGE blocks
_BOILERPLATE_MAX_DENSITY = 0.5   # financial figures per 1000 chars


def condense_for_prompt(text: str) -> str:
    """Drop page-sized blocks with too few financial figures to be useful for
    extraction, to keep the prompt sent to the model focused on the pages
    that actually carry account data. Used ONLY for building the model
    prompt — R8 validation always runs against the full, untrimmed text from
    extract_text(), so a figure the model somehow still got right from a
    dropped block still counts as verbatim-in-source."""
    blocks = text.split('\n\n')
    kept = []
    for b in blocks:
        density = len(_financial_numbers(b)) / max(len(b), 1) * 1000
        if len(b) > _BOILERPLATE_MIN_LEN and density < _BOILERPLATE_MAX_DENSITY:
            continue
        kept.append(b)
    return '\n\n'.join(kept)


PDF_STATEMENT_SYSTEM_PROMPT = """You extract structured data from the raw text of a credit card statement. You are a strict transcriber, not a narrator or analyst. Return ONLY a JSON object — no markdown fences, no commentary, no explanation.

Schema:
{
  "transactions": [
    {"date": "YYYY-MM-DD", "description": "string", "amount": number (always positive), "type": "debit" or "credit"}
  ],
  "summary": {
    "newBalance": number or null,
    "apr": number or null,
    "minimumPayment": number or null,
    "interestCharged": number or null,
    "paymentReceived": number or null,
    "statementPeriod": "YYYY-MM-DD" (the statement's closing date) or null
  }
}

Rules:
- Use null for any field that is not printed on the statement. NEVER guess, estimate, round, or infer a figure that is not literally on the page.
- "type": a purchase/charge is "debit"; a payment, credit, or refund is "credit".
- Every number you write must appear verbatim on the statement, as a dollar amount or a percentage. Do not compute, combine, or derive a figure the statement does not state directly.
- transactions[] must include every posted transaction line on the statement — not a sample, not a summary.
"""


def build_user_prompt(statement_text: str) -> str:
    return f'STATEMENT TEXT:\n\n{statement_text}'


def parse_json_response(text: str) -> dict:
    """Strip markdown code fences if the model added them anyway, then parse
    the FIRST balanced JSON object in the text. Small models routinely
    append trailing commentary ("Note: the statement period wasn't found...")
    after an otherwise-valid JSON block despite being told to return only
    JSON — a naive json.loads() on the whole string fails on that trailing
    text even though the JSON itself is fine. Raises json.JSONDecodeError if
    no balanced object can be found at all."""
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', (text or '').strip())
    start = cleaned.find('{')
    if start == -1:
        raise json.JSONDecodeError('No JSON object found in model output', cleaned, 0)
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == '{':
            depth += 1
        elif cleaned[i] == '}':
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start:i + 1])
    raise json.JSONDecodeError('Unbalanced JSON object in model output', cleaned, start)


def validate_and_clean(data: dict, source_text: str) -> tuple:
    """R8-style number provenance, applied to the model's own JSON output:
    null out any summary figure that doesn't literally appear in the source
    text, and drop any transaction whose amount doesn't either. Returns
    (cleaned_data, warnings). The safe failure direction is to null/drop —
    never to keep a number the source text can't back up."""
    warnings = []
    source_nums = _financial_numbers(source_text)

    summary = dict(data.get('summary') or {})
    for field in ('newBalance', 'apr', 'minimumPayment', 'interestCharged', 'paymentReceived'):
        val = summary.get(field)
        if val is None:
            continue
        if not (_number_candidates(val) & source_nums):
            warnings.append(f'summary.{field} ({val}) not found verbatim in the statement text — discarded')
            summary[field] = None
    # statementPeriod is a date, not a financial figure — no provenance check,
    # just a light shape check so a malformed value doesn't reach the DB.
    period = summary.get('statementPeriod')
    if period and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(period)):
        warnings.append(f'summary.statementPeriod ("{period}") is not YYYY-MM-DD — discarded')
        summary['statementPeriod'] = None

    transactions = []
    for i, t in enumerate(data.get('transactions') or []):
        amt = t.get('amount') if isinstance(t, dict) else None
        if amt is None or not (_number_candidates(amt) & source_nums):
            warnings.append(f'transaction #{i + 1} amount ({amt}) not found verbatim in the statement text — dropped')
            continue
        if not t.get('date') or not re.match(r'^\d{4}-\d{2}-\d{2}$', str(t.get('date'))):
            warnings.append(f'transaction #{i + 1} has no valid date — dropped')
            continue
        transactions.append(t)

    # A missed statementPeriod blocks reconciliation entirely downstream (the
    # whole point of the feature), and small models miss this field far more
    # than the dollar figures. Fall back to the latest validated transaction's
    # date — not a fabrication, since every transaction date here has already
    # passed R8 provenance. Mirrors the existing B6b auto-write's own fallback
    # (server.py: statement_period_end = date of the last imported transaction).
    if not summary.get('statementPeriod') and transactions:
        latest = max(t['date'] for t in transactions)
        summary['statementPeriod'] = latest
        warnings.append(f'statementPeriod not found on the statement — inferred as {latest} '
                         f'from the latest transaction date')

    return {'transactions': transactions, 'summary': summary}, warnings
