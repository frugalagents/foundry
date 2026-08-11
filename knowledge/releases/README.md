# Generated Knowledge Releases

Everything below this directory is generated output. Do not edit release files
manually.

Rebuild the pinned coding-platform release:

```bash
python3 tools/knowledge/export_legacy_migration.py
python3 tools/knowledge/build_release.py
```

The release tests independently rebuild the migration and release, validate
every file hash and size, and compare the resulting typed manifest with the
checked-in artifacts. Any manual change fails CI unless the source knowledge,
scenario suite, compiler output, and generated release are updated together.

Published releases are immutable. A new knowledge state requires a new release
version; existing release paths must never be overwritten.
