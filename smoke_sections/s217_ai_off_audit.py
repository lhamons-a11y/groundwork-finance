"""The AI-off audit (item 32 L4 / ASKED_FACTS A10; gw 2.0/AI_OFF_AUDIT.md, 2026-10-12): every surface complete with AI
off, and with AI on but unable to run. What the audit found and fixed, held here.

    F1  Trophies: with AI off the money story is the facts, never a "Generate" that shows the model's input
    F2  the monthly report's note label says "AI reads this" only when AI is on
    F3  the trip planner: learning from a past trip is hidden without AI; reading a pasted quote says it needs AI
        and points at the itinerary reader, which needs none
    F5  a model that can never run here (processor, missing / mismatched file, failed load) is AI off for every
        surface, and the sidebar says AI is unavailable, with the engine's own reason
    F6  the Ask box: with AI off or unable to run, a question about the records still reaches the checks, chosen by
        the person from the fixed list
"""
import json


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    app, html = ctx.app_src, ctx.html_src
    from core import engine
    from core.database import AppSetting, db_session

    data = lambda r: (r.get_json() or {}).get('data') or {}

    def set_ai(v):
        with db_session() as s:
            s.query(AppSetting).filter_by(key='ai_enabled').delete()
            if v is not None:
                s.add(AppSetting(key='ai_enabled', value=v))
            s.commit()

    with db_session() as s:
        row = s.query(AppSetting).filter_by(key='ai_enabled').first()
        before = row.value if row else None
    saved = dict(engine._state)
    try:
        set_ai('false')
        chat = data(c.post('/api/ai/chat', headers=HJ, data=json.dumps({'messages': [{'role': 'user', 'content': 'hi'}]})))
        off = data(c.post('/api/why/route', headers=HJ, data=json.dumps({'question': 'duplicate transactions'})))
        check(f"s217 A10 AI off: the model is never asked, and a question about the records is offered the checks ({off.get('state')}, {len(off.get('checks', []))})",
              chat.get('ai_available') is False and off.get('state') == 'off' and len(off.get('checks', [])) >= 5)
        set_ai('true')
        engine._state.update(state='unavailable', reason='missing', detail='')
        st = data(c.get('/api/ai/status', headers=HJ))
        cant = data(c.post('/api/why/route', headers=HJ, data=json.dumps({'question': 'duplicate transactions'})))
        check(f"s217 F5/F6 AI on but unable to run (a missing model file): the status names why, and the Ask box still offers the checks ({st.get('engine')}, {cant.get('state')})",
              st.get('enabled') and st.get('engine') == 'unavailable' and 'missing' in (st.get('message') or '')
              and cant.get('state') == 'off' and len(cant.get('checks', [])) >= 5)
    finally:
        engine._state.clear(); engine._state.update(saved)
        set_ai(before)

    ai = app.split('function aiEnabled() {')[1].split('\n}\n')[0]
    can = app.split('async function _checkAiCanRun() {')[1].split('\n}\n')[0]
    vis = app.split('function updateAIFeatureVisibility() {')[1].split('\n}\n')[0]
    check('s217 F5 a model that can never run here is AI off for every surface, and the sidebar says it is unavailable with the reason',
          'if (_aiCannotRun) return false;' in ai and "st.engine === 'unavailable'" in can and "st.engine === 'loading'" in can
          and "'AI unavailable on this computer'" in vis and 'status.title = _aiCannotRun' in vis
          and '_checkAiCanRun();   // AI-off audit F5' in app)
    trophy = app.split('function _trophyRenderAdvisorEntry(earnedN) {')[1].split('\n}\n')[0]
    check('s217 F1 Trophies with AI off: the facts, complete - no Generate, no model input on the page',
          'if (!aiEnabled()) {' in trophy and 'achievements earned' in trophy
          and trophy.index('if (!aiEnabled()) {') < trophy.index('_trophyLaunchAdvisorAI'))
    quote = app.split('async function _readTripQuote() {')[1].split('\n}\n')[0]
    check('s217 F3 the trip planner without AI: learning from a past trip is hidden; a pasted quote says it needs AI and points at the itinerary reader',
          'id="tripLearnCard" class="card mb-5 ai-feature"' in html and quote.lstrip().startswith('if (!aiEnabled()) {')
          and 'Read as a whole itinerary' in quote.split('return;')[0])
    check('s217 F2 "AI reads this" is said only when AI is on',
          "${aiEnabled() ? '(AI reads this)' : '(kept with this report)'}" in app
          and '<span class="ai-feature" style="font-size:10px;color:rgba(255,255,255,.62)">AI reads this</span>' in html)
    ask = app.split('async function askGroundwork(question) {')[1].split('\nfunction ')[0]
    check('s217 F6 the Ask box asks the server even with AI off, and offers the fixed checks when no model answers',
          "route.state === 'off' && (route.checks || []).length" in ask and 'you choose the check' in ask
          and 'if (aiEnabled()) {\n    let route' not in ask)
