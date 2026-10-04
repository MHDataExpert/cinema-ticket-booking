"""Persian search normalization: ي/ی, ك/ک, half-space, fa/ar digits."""

import re

_AR_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_fa(s: str) -> str:
    s = s.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک").replace("ة", "ه")
    s = s.translate(_AR_FA_DIGITS)
    s = s.replace("‌", " ").replace("‍", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def like_pattern(term: str) -> str:
    """Normalized term -> ILIKE pattern; half-space becomes wildcard so «بچه‌های» matches «بچه های»."""
    t = normalize_fa(term)
    t = t.replace(" ", "%")
    return f"%{t}%"
