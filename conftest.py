# Root conftest so pytest puts the repository root on sys.path (`import app` works).
import os

# Set before app.config is imported, so tests never need a .env file.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://newbid:newbid@localhost:5432/newbid_test")
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long")
# Lowest bcrypt cost, so tests that hash passwords stay fast.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("SETTLE_INTERVAL_SECONDS", "0")
