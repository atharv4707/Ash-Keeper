from app.core.security import hash_password, verify_password


def test_hash_password_uses_bcrypt_and_verifies_round_trip():
    plain = "Password123!"
    hashed = hash_password(plain)

    assert hashed.startswith("$2b$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
