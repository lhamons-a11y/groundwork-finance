"""
Groundwork — isolated dev server for browser-testing UI changes.

Runs the Flask app against a throwaway temp DB (never the real
%LOCALAPPDATA%\\Groundwork database) so UI work can be exercised in a
browser without any risk to real financial data. Not the packaged app
entry point — see launch.py for that.

Usage: python dev_server.py
"""
import os
import sys
import tempfile

_PORT = int(os.environ.get('PORT') or os.environ.get('GW_DEV_PORT') or 8766)     # a second preview beside a running one: its own port and temp DB
_tmp = os.path.join(tempfile.gettempdir(), 'gw_dev_server' + ('' if _PORT == 8766 else f'_{_PORT}'))
os.makedirs(_tmp, exist_ok=True)
os.environ['GROUNDWORK_DATA_DIR'] = _tmp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    import server
    from server import create_app, serve
    server._PAGE_GATE = False          # a throwaway database opened from an ordinary browser: no page key to hand it
    app = create_app()
    print(f'Groundwork dev server — temp DB at {_tmp}', flush=True)
    if os.environ.get('GROUNDWORK_DEV_ENGINE') == '1':     # opt in: load the model as the launcher does (AI on only)
        from server import engine_launch
        engine_launch()
    # The same server the packaged app uses. A dev server on different
    # machinery measures the wrong thing, and latency was measured here.
    serve(app, host='127.0.0.1', port=_PORT)
