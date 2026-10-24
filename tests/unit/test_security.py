from app.infra.security import BcryptHasher


def test_bcrypt_hash_verifies_only_the_same_password():
    hasher = BcryptHasher(rounds=4)
    hashed = hasher.hash("matkhau123")

    assert hasher.verify("matkhau123", hashed)
    assert not hasher.verify("matkhau124", hashed)


def test_bcrypt_rejects_password_over_72_bytes_instead_of_raising():
    hasher = BcryptHasher(rounds=4)

    assert not hasher.verify("a" * 73, hasher.hash("matkhau123"))
