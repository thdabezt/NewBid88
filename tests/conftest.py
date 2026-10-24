from datetime import datetime

import pytest

from app.services import bids
from tests.fakes import BidsMemoryDb, FixedClock


@pytest.fixture()
def bids_now(monkeypatch):
    """Co dinh gio cua service, de test moc 60 giay khong bi lech."""
    clock = FixedClock()

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.now()

    monkeypatch.setattr(bids, "datetime", FrozenDatetime)
    return clock.now()


@pytest.fixture()
def bids_db(bids_now):
    return BidsMemoryDb(bids_now)