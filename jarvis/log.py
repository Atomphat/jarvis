import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(name: str, logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        logs_dir / f"{name}.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
