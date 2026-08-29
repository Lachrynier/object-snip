from types import SimpleNamespace

import pytest

from objectsnip.segmentation.sam2 import select_device


def torch_capabilities(cuda: bool = False, mps: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: cuda),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)),
    )


def test_device_selection_prefers_cuda_then_mps_then_cpu() -> None:
    assert select_device(torch_capabilities(cuda=True, mps=True)) == "cuda"
    assert select_device(torch_capabilities(mps=True)) == "mps"
    assert select_device(torch_capabilities()) == "cpu"


def test_explicit_unavailable_accelerator_is_an_error() -> None:
    with pytest.raises(RuntimeError):
        select_device(torch_capabilities(), "cuda")
    with pytest.raises(RuntimeError):
        select_device(torch_capabilities(), "mps")


def test_explicit_cpu_is_always_available() -> None:
    assert select_device(torch_capabilities(cuda=True), "cpu") == "cpu"
