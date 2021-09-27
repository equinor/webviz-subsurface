import io
import json
from pathlib import Path

from webviz_config.webviz_store import webvizstore


@webvizstore
def get_path(path: str) -> Path:
    return Path(path)


@webvizstore
def find_files(folder: Path, suffix: str) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )
