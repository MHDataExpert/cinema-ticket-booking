from app.fa import like_pattern, normalize_fa


def test_normalize_digits_and_letters():
    assert normalize_fa("بچه‌های ۱۲٣") == "بچه های 123"
    assert normalize_fa("سيمين كاو") == "سیمین کاو"


def test_like_pattern_halfspace():
    p = like_pattern("بچه‌های آسمان")
    assert p.startswith("%") and p.endswith("%") and "%%" not in p
