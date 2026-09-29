"""Cleans job links before they are stored.

Job-alert emails wrap every link in click trackers, and some (e.g. Naukrigulf) embed a token that logs the
reader straight into the candidate's account. Only the plain public job page is ever stored.
"""

from __future__ import annotations

import re
import urllib.parse

# Path patterns of login / auto-login pages (query strings are always dropped).
_LOGIN_PATH = re.compile(r"(^|/)([a-z]*login|signin|sign-in|sso|oauth|auth|session|mailerlogin)(/|$)", re.IGNORECASE)
# Redirect parameters used by trackers to carry the real destination.
_REDIRECT_KEYS = ("rUrl", "rurl", "redirect", "url", "u", "target", "dest", "destination")


class UnsafeUrlError(ValueError):
    pass


def _unwrap(url: str, depth: int = 0) -> str:
    """Follow tracker redirect parameters (without any network call) to the final destination."""
    if depth > 5:
        return url
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    for key in _REDIRECT_KEYS:
        for value in params.get(key, []):
            if value.startswith(("http://", "https://")):
                return _unwrap(value, depth + 1)
    return url


def clean_job_url(url: str) -> str:
    """Return the tracker-free, token-free public URL of a job page.

    Raises UnsafeUrlError if what remains still looks like a login link.
    """
    final = _unwrap(url.strip())
    parts = urllib.parse.urlparse(final)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise UnsafeUrlError("not a web link")
    cleaned = urllib.parse.urlunparse((parts.scheme, parts.netloc.lower(), parts.path, "", "", ""))
    if _LOGIN_PATH.search(parts.path):
        raise UnsafeUrlError("link still points to a login page")
    return cleaned
