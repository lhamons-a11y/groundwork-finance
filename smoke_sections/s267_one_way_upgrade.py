"""Item 82 L3c (Rob 2026-10-31: "lets not let a 2.0 database be open by a previous version" ... "in windows the installer
should check for previous versions and uninstall them for the user and then install 2.0. Mac, linux the files should
overwrite the previous"). Measured first (scripts/l3c_one_way.py): a released 1.1.1 opens a 2.0 database, reads and
writes it and writes its own version back.

    2.0 notices it: a 2.0 database (its own tables there) carrying a 1.x version is said once, with the way back
    Windows: the installer removes an earlier Groundwork silently first - the uninstaller never touches the records
    Linux: the install script replaces the earlier program folder, and never the records
    The help guide and the download page say the update goes one way, and how to go back
"""
import re


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    import server
    from core.database import db_session, AppSetting
    check('s267 2.0 notices a 2.0 database a 1.x has opened (its version set back, 2.0\'s own tables there) - and only that',
          server._opened_by_1x('20261002-lts-household-facts') is True and server._opened_by_1x('20260725-byb') is True
          and server._opened_by_1x('20261030-goal-accounts') is False and server._opened_by_1x(None) is False)
    js = ctx.app_src
    check('s267 it is said once, in the upgrade notice: nothing lost, the UTC times, and the way back',
          "Groundwork 1.1 opened these records" in js and "restore the copy saved before your" in js
          and "r.opened_by_1x ? 'Groundwork 1.1 opened your records'" in js
          and "rec['opened_by_1x'] = stored" in ctx.server_src)
    check('s267 the help guide answers "Can I go back to Groundwork 1.1?"', '"q": "Can I go back to Groundwork 1.1?"' in js)

    for f in ('groundwork.iss', 'groundwork_offline.iss'):
        src = (BASE / f).read_text(encoding='utf-8')
        app_id = re.search(r'AppId=\{\{([0-9A-F-]+)\}', src).group(1)
        code = src.split('[Code]', 1)[1]
        check(f's267 {f}: an earlier Groundwork (this AppId) is removed silently before installing; an open one is closed; '
              f'the records are never touched',
              f'{{{app_id}}}_is1' in code and 'function PrepareToInstall(' in code
              and "'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'" in code and 'ewWaitUntilTerminated' in code
              and 'CloseApplications=yes' in src and re.search(r'\[UninstallDelete\]\s*Type: filesandordirs; Name: "\{app\}"\s*\[', src)
              and 'localappdata' not in src.split('[UninstallDelete]', 1)[1].split('[Code]', 1)[0].lower())
    sh = (BASE / 'install_linux.sh').read_text(encoding='utf-8')
    removes = re.findall(r'rm -rf (\S+)', sh)
    check(f's267 Linux: the install script replaces the earlier program folder and nothing else ({removes})',
          removes == ['"${INSTALL_DIR:?}"'] and 'INSTALL_DIR="/opt/groundwork"' in sh and '.local/share' not in ''.join(removes))
    site = (BASE / 'Website' / 'website.py').read_text(encoding='utf-8')
    check('s267 the download page (once 2.0 is the download) says how each platform replaces the earlier version, and '
          'that the update goes one way',
          'the installer removes the earlier version for you' in site and 'choose <strong>Replace</strong>' in site
          and 'install \'\n            \'script replaces the earlier version' in site or 'script replaces the earlier version' in site)
