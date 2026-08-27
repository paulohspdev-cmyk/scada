import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_manifests(base: Path, scope: str):
    items = []
    if not base.exists():
        return items
    for path in sorted(base.rglob("manifest.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        data["scope"] = scope
        data["pack_path"] = str(path.relative_to(ROOT))
        items.append(data)
    return items


def list_controller_packs():
    return _read_manifests(ROOT / "controllers", "production") + _read_manifests(
        ROOT / "lab" / "controllers", "lab"
    )
