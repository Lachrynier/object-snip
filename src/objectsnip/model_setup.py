from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

MODEL_URL = (
    "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"
)
MODEL_SHA256 = "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69"
DEFAULT_OUTPUT = Path(".models/sam2.1_hiera_tiny.pt")


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(output: Path) -> None:
    if output.is_file() and file_sha256(output) == MODEL_SHA256:
        print(f"SAM 2.1 Tiny is already installed at {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.part")
    try:
        with urlopen(MODEL_URL) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        actual_hash = file_sha256(temporary)
        if actual_hash != MODEL_SHA256:
            raise RuntimeError(
                f"checkpoint checksum mismatch: expected {MODEL_SHA256}, "
                f"received {actual_hash}"
            )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Installed SAM 2.1 Tiny at {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    download_model(arguments.output)
