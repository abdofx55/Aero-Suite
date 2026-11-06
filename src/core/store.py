"""
store.py — Central MVI AppStore for Aero Suite.
Manages application state updates and emits Qt signals upon state changes.
"""
from PySide6.QtCore import QObject, Signal
from core.state import AppState, Intent, app_reducer


class AppStore(QObject):
    """
    Central Store managing the single source of truth (AppState).
    Components dispatch Intents to this store and subscribe to state_changed signals.
    """
    state_changed = Signal(object)  # Emits new AppState instance

    def __init__(self, initial_state: AppState = None):
        super().__init__()
        self._state = initial_state or AppState()

    @property
    def state(self) -> AppState:
        """Returns the current immutable application state."""
        return self._state

    def dispatch(self, intent: Intent):
        """Processes an intent through the reducer and notifies subscribers if state changed."""
        if not isinstance(intent, Intent):
            raise TypeError(f"Expected Intent instance, got {type(intent)}")

        old_state = self._state
        new_state = app_reducer(old_state, intent)

        if new_state is not old_state:
            self._state = new_state
            self.state_changed.emit(new_state)


# Global Store Singleton
_GLOBAL_STORE: AppStore = None


def get_store() -> AppStore:
    """Returns the singleton AppStore instance."""
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        _GLOBAL_STORE = AppStore()
    return _GLOBAL_STORE
