"""
Groundwork — Version Information
Single source of truth for the application version.
"""

VERSION       = "2.0.0.0"
VERSION_TUPLE = (2, 0, 0, 0)
APP_NAME      = "Groundwork"
RELEASE_YEAR  = "2026"

# The live update check reads a static manifest from the website
# (see server.py UPDATE_MANIFEST_URL). Groundwork does not depend on the
# GitHub releases API.
