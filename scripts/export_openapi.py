"""Dump the service OpenAPI schema to docs.json."""

import json
from pathlib import Path

from app.main import app


def main() -> None:
    schema = app.openapi()
    out = Path("docs.json")
    out.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
