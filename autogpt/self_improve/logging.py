"""Exception and logging utilities."""

from __future__ import annotations

import logging
import sys
import traceback
from types import TracebackType
from pathlib import Path

from .database import DatabaseManager


def install_exception_logger(
    db: DatabaseManager, log_path: Path | str | None = None
) -> None:
    """Install a global exception hook that stores exceptions in the DB."""

    log_file = Path(log_path or "self_improve.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        filename=log_file,
    )

    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        db.log_error(str(exc_value), traceback_str)

    sys.excepthook = handle_exception
