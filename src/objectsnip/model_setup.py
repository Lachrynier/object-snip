from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

from objectsnip.segmentation.models import (
    DEFAULT_SAM2_MODEL,
    SAM2_MODEL_NAMES,
    SAM2_MODELS,
    Sam2Model,
)

MODEL_URL = SAM2_MODELS[DEFAULT_SAM2_MODEL].url
MODEL_SHA256 = SAM2_MODELS[DEFAULT_SAM2_MODEL].sha256
DEFAULT_OUTPUT = SAM2_MODELS[DEFAULT_SAM2_MODEL].checkpoint


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(model: Sam2Model, output: Path) -> None:
    if output.is_file() and file_sha256(output) == model.sha256:
        print(f"SAM 2.1 {model.name} is already installed at {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.part")
    try:
        with urlopen(model.url) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        actual_hash = file_sha256(temporary)
        if actual_hash != model.sha256:
            raise RuntimeError(
                f"checkpoint checksum mismatch: expected {model.sha256}, "
                f"received {actual_hash}"
            )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Installed SAM 2.1 {model.name} at {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=SAM2_MODEL_NAMES, default=DEFAULT_SAM2_MODEL)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    model = SAM2_MODELS[arguments.model]
    download_model(model, arguments.output or model.checkpoint)
