import threading
import time

from app.workers.settler import Settler


class FakeSettlementService:
    def __init__(self, due_ids, failing=()):
        self.due_ids = list(due_ids)
        self.failing = set(failing)
        self.settled = []
        self.ran = threading.Event()

    def due(self, limit):
        self.ran.set()
        return self.due_ids[:limit]

    def settle(self, auction_id):
        if auction_id in self.failing:
            raise RuntimeError("boom")
        self.settled.append(auction_id)
        self.due_ids.remove(auction_id)
        return "SOLD"


def test_run_once_keeps_going_after_a_failure():
    service = FakeSettlementService([1, 2, 3], failing={2})

    assert Settler(service, interval=60, batch=10).run_once() == 2

    assert service.settled == [1, 3]


def test_run_once_counts_only_settled_auctions():
    service = FakeSettlementService([1, 2])
    service.settle = lambda auction_id: None

    assert Settler(service, interval=60, batch=10).run_once() == 0


def test_start_runs_in_background_and_stop_joins():
    service = FakeSettlementService([1])
    settler = Settler(service, interval=60, batch=10)

    settler.start()
    assert service.ran.wait(timeout=2)
    settler.stop()

    assert service.settled == [1]


def test_full_batch_is_followed_by_another_run_without_waiting():
    service = FakeSettlementService([1, 2, 3])
    settler = Settler(service, interval=60, batch=2)

    settler.start()
    for _ in range(200):
        if not service.due_ids:
            break
        time.sleep(0.01)
    settler.stop()

    assert service.settled == [1, 2, 3]


def test_stop_without_start_is_safe():
    Settler(FakeSettlementService([]), interval=60, batch=10).stop()
