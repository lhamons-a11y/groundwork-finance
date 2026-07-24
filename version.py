"""
Groundwork — Version Information
Single source of truth for the application version.
"""

VERSION       = "1.0.0.0"
VERSION_TUPLE = (1, 0, 0, 0)
APP_NAME      = "Groundwork"
RELEASE_YEAR  = "2026"
GITHUB_OWNER  = "your-github-username"   # UPDATE before release
GITHUB_REPO   = "groundwork"             # UPDATE before release

# GitHub releases API — used by auto-update check
RELEASES_API  = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
