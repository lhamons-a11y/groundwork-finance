"""
Send one file to the operating system's Recycle Bin / Trash - never delete it.

`gw 2.0/SOURCE_DOCUMENT_CUSTODY.md` H2: when the user removes a downloaded bank file after importing it, the file goes
where they can get it back. Each platform's route is a library Groundwork already ships, so there is no new
dependency:

    Windows   SHFileOperationW with FOF_ALLOWUNDO, through ctypes
    macOS     NSFileManager.trashItemAtURL, through PyObjC (already required for the pywebview window)
    Linux     Gio.File.trash, through PyGObject (already required for the GTK window)

If none is available, or the call fails, the answer is (False, reason) and the file is left exactly where it was.
There is deliberately no fallback to permanent deletion anywhere in this module: s128 fails if one appears.
"""

import os
import sys


def send_to_recycle_bin(path):
    """(True, '') once the file is in the Recycle Bin / Trash, else (False, reason). Never deletes."""
    path = os.path.abspath(str(path))
    if not os.path.isfile(path):
        return False, 'gone'
    try:
        if sys.platform == 'win32':
            ok = _windows(path)
        elif sys.platform == 'darwin':
            ok = _macos(path)
        else:
            ok = _linux(path)
    except Exception:                                   # noqa: BLE001 - any failure leaves the file alone
        return False, 'recycle_unavailable'
    if ok and not os.path.exists(path):
        return True, ''
    return False, 'recycle_unavailable'


def _windows(path):
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT),
                    ('pFrom', wintypes.LPCWSTR), ('pTo', wintypes.LPCWSTR),
                    ('fFlags', ctypes.c_uint16), ('fAnyOperationsAborted', wintypes.BOOL),
                    ('hNameMappings', ctypes.c_void_p), ('lpszProgressTitle', wintypes.LPCWSTR)]

    FO_DELETE = 3
    FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = path + '\0'                              # the API wants a double-NUL-terminated list
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return result == 0 and not op.fAnyOperationsAborted


def _macos(path):
    from Foundation import NSFileManager, NSURL
    ok, _url, _err = NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(
        NSURL.fileURLWithPath_(path), None, None)
    return bool(ok)


def _linux(path):
    from gi.repository import Gio
    return bool(Gio.File.new_for_path(path).trash(None))
