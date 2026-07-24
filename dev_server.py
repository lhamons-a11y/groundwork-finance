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

_tmp = os.path.join(tempfile.gettempdir(), 'gw_dev_server')
os.makedirs(_tmp, exist_ok=True)
os.environ['GROUNDWORK_DATA_DIR'] = _tmp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    from server import create_app
    app = create_app()
    print(f'Groundwork dev server — temp DB at {_tmp}', flush=True)
    app.run(host='127.0.0.1', port=8766, debug=False, threaded=True)
