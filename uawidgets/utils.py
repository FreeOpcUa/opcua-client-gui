import inspect
import logging
from typing import Any, Callable, TypeVar, cast


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def trycatchslot(func: F) -> F:
    """
    wrap a Qt slot.
    log and call a method called show_error or a signal
    called error in case of error
    """
    def wrapper(self: Any, *args: Any) -> Any:
        sig = inspect.signature(func)
        args = args[:(len(sig.parameters) - 1)]
        result: Any = None
        try:
            result = func(self, *args)
        except Exception as ex:
            logger.exception(ex)
            if hasattr(self, "show_error"):
                self.show_error(ex)
            elif hasattr(self, "error"):
                self.error.emit(ex)
            else:
                logger.warning("Error class %s has no member show_error or error", self)
        return result
    return cast(F, wrapper)
