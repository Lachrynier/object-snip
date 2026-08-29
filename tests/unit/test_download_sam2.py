from hashlib import sha256

from objectsnip.model_setup import MODEL_SHA256, file_sha256
from objectsnip.segmentation.models import SAM2_MODELS


def test_file_sha256_reads_checkpoint_in_chunks(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "model.pt"
    content = b"objectsnip-test-model"
    path.write_bytes(content)

    assert file_sha256(path) == sha256(content).hexdigest()
    assert len(MODEL_SHA256) == 64
    assert all(len(model.sha256) == 64 for model in SAM2_MODELS.values())
