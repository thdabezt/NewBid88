import logging
import threading

from app.services.settlement import SettlementService

logger = logging.getLogger(__name__)


class Settler:
    def __init__(self, service: SettlementService, interval: float, batch: int) -> None:
        self._service = service
        self._interval = interval
        self._batch = batch
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="settler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def run_once(self) -> int:
        settled = 0
        for auction_id in self._service.due(self._batch):
            try:
                if self._service.settle(auction_id):
                    settled += 1
            except Exception:
                logger.exception("Could not settle auction %s", auction_id)
        return settled

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                settled = self.run_once()
            except Exception:
                logger.exception("Settlement run failed")
                settled = 0
            if settled < self._batch:
                self._stop.wait(self._interval)
