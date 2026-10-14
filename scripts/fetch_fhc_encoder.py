"""Download the pinned MiniLM encoder used by the F/H/C release model.

Run at Railway build time (after pip install) so the 90 MB encoder is not
committed to git. The revision is pinned to the one the model was trained with
(data/models/minilm-base/pally_source.json on the training machine).
"""
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

REPO_ID = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DEST = Path(__file__).resolve().parents[1] / "data" / "models" / "minilm-base"


def main() -> None:
    snapshot_download(repo_id=REPO_ID, revision=REVISION, local_dir=DEST,
                      allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*"])
    weights = DEST / "model.safetensors"
    if not weights.is_file() or weights.stat().st_size < 1_000_000:
        sys.exit(f"encoder download incomplete: {weights}")
    print(f"encoder ready at {DEST}")


if __name__ == "__main__":
    main()
