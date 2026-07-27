from app.security import COOKIE


def test_cookie_name_is_stable():
    assert COOKIE == "wg_session"
