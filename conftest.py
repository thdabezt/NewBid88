import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://newbid:newbid@localhost:5432/newbid_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("SETTLE_INTERVAL_SECONDS", "0")
