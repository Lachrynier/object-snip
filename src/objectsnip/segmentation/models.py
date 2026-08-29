from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sam2Model:
    name: str
    config: str
    checkpoint: Path
    url: str
    sha256: str


_BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824"

SAM2_MODELS = {
    "tiny": Sam2Model(
        "tiny",
        "configs/sam2.1/sam2.1_hiera_t.yaml",
        Path(".models/sam2.1_hiera_tiny.pt"),
        f"{_BASE_URL}/sam2.1_hiera_tiny.pt",
        "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69",
    ),
    "small": Sam2Model(
        "small",
        "configs/sam2.1/sam2.1_hiera_s.yaml",
        Path(".models/sam2.1_hiera_small.pt"),
        f"{_BASE_URL}/sam2.1_hiera_small.pt",
        "6d1aa6f30de5c92224f8172114de081d104bbd23dd9dc5c58996f0cad5dc4d38",
    ),
    "base-plus": Sam2Model(
        "base-plus",
        "configs/sam2.1/sam2.1_hiera_b+.yaml",
        Path(".models/sam2.1_hiera_base_plus.pt"),
        f"{_BASE_URL}/sam2.1_hiera_base_plus.pt",
        "a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5",
    ),
    "large": Sam2Model(
        "large",
        "configs/sam2.1/sam2.1_hiera_l.yaml",
        Path(".models/sam2.1_hiera_large.pt"),
        f"{_BASE_URL}/sam2.1_hiera_large.pt",
        "2647878d5dfa5098f2f8649825738a9345572bae2d4350a2468587ece47dd318",
    ),
}

DEFAULT_SAM2_MODEL = "tiny"
SAM2_MODEL_NAMES = tuple(SAM2_MODELS)
