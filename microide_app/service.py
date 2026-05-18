from typing import Optional, Dict, Any
from microide_core import InputTracker


class RecorderService:
    """
    Сервис управления записью (аналог Selenium Recorder layer).
    """

    def __init__(self):
        self._tracker: Optional[InputTracker] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self.on_keyword = None        # внешний callback (GUI)
        self.on_pause_changed = None  # внешний callback (GUI): fn(is_paused: bool)

    def _handle_keyword(self, keyword: str):
        if self.on_keyword:
            self.on_keyword(keyword)

    def start(self):
        if self._tracker and self._tracker.is_tracking:
            return
        # Сохраняем кэш UI от предыдущей записи — он остаётся валидным,
        # т.к. AutomationId приложения не меняются между тестами
        old_cache = self._tracker._ui_cache if self._tracker else None
        self._tracker = InputTracker()
        if old_cache:
            self._tracker._ui_cache = old_cache
        self._tracker.on_keyword = self._handle_keyword
        self._tracker.on_pause_changed = self.on_pause_changed

    def run_blocking(self) -> Optional[Dict[str, Any]]:
        """
        Запускает запись в текущем потоке.
        Остановка: ESC → пауза → ESC → стоп
        """
        if not self._tracker:
            self.start()

        result = self._tracker.run()
        self._last_result = result
        return result

    @property
    def last_result(self):
        return self._last_result

    def stop(self):
        if self._tracker:
            self._tracker.request_stop()
