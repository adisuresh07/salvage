from __future__ import annotations

import json

from salvage.api.app import create_app
from salvage.config import ROOT, Settings


def main() -> None:
    target = ROOT / "openapi.json"
    target.write_text(
        json.dumps(
            create_app(Settings(_env_file=None, simulator_enabled=True)).openapi(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(target)


if __name__ == "__main__":
    main()
