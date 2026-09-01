from hashlib import sha256
from pathlib import Path

from objectsnip.model_setup import MODEL_SHA256, ensure_model, file_sha256
from objectsnip.segmentation.models import SAM2_MODELS, Sam2Model


def test_file_sha256_reads_checkpoint_in_chunks(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "model.pt"
    content = b"objectsnip-test-model"
    path.write_bytes(content)

    assert file_sha256(path) == sha256(content).hexdigest()
    assert len(MODEL_SHA256) == 64
    assert all(len(model.sha256) == 64 for model in SAM2_MODELS.values())


def test_ensure_model_downloads_a_missing_checkpoint(
    tmp_path, monkeypatch, capsys
) -> None:  # type: ignore[no-untyped-def]
    checkpoint = tmp_path / "model.pt"
    model = Sam2Model(
        "test", "config.yaml", checkpoint, "https://example.test", "0" * 64
    )
    downloaded: list[tuple[Sam2Model, Path]] = []
    monkeypatch.setattr(
        "objectsnip.model_setup.download_model",
        lambda selected, output: downloaded.append((selected, output)),
    )

    ensure_model(model)

    assert downloaded == [(model, checkpoint)]
    assert "Downloading SAM 2.1 test" in capsys.readouterr().out


def test_ensure_model_leaves_an_existing_checkpoint_alone(
    tmp_path, monkeypatch, capsys
) -> None:  # type: ignore[no-untyped-def]
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"already installed")
    model = Sam2Model(
        "test", "config.yaml", checkpoint, "https://example.test", "0" * 64
    )
    downloaded: list[tuple[Sam2Model, Path]] = []
    monkeypatch.setattr(
        "objectsnip.model_setup.download_model",
        lambda selected, output: downloaded.append((selected, output)),
    )

    ensure_model(model)

    assert downloaded == []
    assert capsys.readouterr().out == ""
