#!/usr/bin/env python3
"""Verify a packaged runtime release using only the standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-manifest-hash", required=True)
    args = parser.parse_args()

    root = args.release_root.resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("release_version") != args.expected_version:
        raise SystemExit("release version does not match the configured pin")
    if manifest.get("manifest_hash") != args.expected_manifest_hash:
        raise SystemExit("release manifest hash does not match the configured pin")

    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise SystemExit("release manifest has no file inventory")
    listed = {record["path"] for record in records}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if listed != actual:
        raise SystemExit(
            "release file inventory mismatch: "
            f"missing={sorted(listed - actual)}, "
            f"unexpected={sorted(actual - listed)}"
        )
    for record in records:
        raw = (root / record["path"]).read_bytes()
        if len(raw) != record["size_bytes"]:
            raise SystemExit(f"release size mismatch: {record['path']}")
        if _sha256(raw) != record["content_hash"]:
            raise SystemExit(f"release hash mismatch: {record['path']}")
    print(
        f"Verified knowledge release {args.expected_version} "
        f"({args.expected_manifest_hash})."
    )


if __name__ == "__main__":
    main()
