from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from okf_compiler import OKFCompileError, compile_okf_release, validate_okf_graph

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def test_compile_okf_release_builds_manifest_and_writes_artifact(tmp_path: Path):
    out_file = tmp_path / "okf-release.json"

    release = compile_okf_release(KNOWLEDGE_DIR, output_path=out_file)

    assert release.manifest.schema_version == "okf.release.v1alpha1"
    assert release.manifest.node_count == len(list(KNOWLEDGE_DIR.rglob("*.md")))
    assert release.manifest.advisory_slice_count >= 4
    assert release.manifest.typed_edge_count > 0
    assert len(release.manifest.graph_sha256) == 64
    assert out_file.exists()

    written = json.loads(out_file.read_text(encoding="utf-8"))
    assert written["manifest"]["graph_sha256"] == release.manifest.graph_sha256
    export_control = next(node for node in written["nodes"] if node["path"] == "access/export-control")
    assert export_control["typed_edges"]["requires"] == ["access/identity"]


def test_validate_okf_graph_reports_broken_typed_edge_target(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    _write_node(
        knowledge_dir / "root.md",
        """---
title: Root
group: root
traversal: mandate
decision-domain: foundation
requires: [missing/node]
---

# Root
""",
    )

    _, issues = validate_okf_graph(knowledge_dir)

    assert [issue.type for issue in issues] == ["missing_edge_target"]
    assert issues[0].node == "root"
    assert issues[0].field == "typed_edges.requires"
    assert issues[0].target == "missing/node"


def test_compile_okf_release_fails_on_invalid_advisory_shape(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    _write_node(
        knowledge_dir / "slice.md",
        """---
title: Slice
group: decision-slices
traversal: conditional
decision-domain: execution_boundary
advisory:
  slice: true
  output:
    question: invalid
---

# Slice
""",
    )

    with pytest.raises(OKFCompileError) as exc_info:
        compile_okf_release(knowledge_dir)

    issues = exc_info.value.issues
    assert [issue.type for issue in issues] == ["invalid_advisory_metadata"]
    assert issues[0].node == "slice"
    assert issues[0].field == "advisory.output.question"


def test_compile_okf_release_fails_on_invalid_node_schema(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    _write_node(
        knowledge_dir / "bad.md",
        """---
title: Bad Node
group: access
traversal: unsupported
decision-domain: compliance_boundary
---

# Bad Node
""",
    )

    with pytest.raises(OKFCompileError) as exc_info:
        compile_okf_release(knowledge_dir)

    issues = exc_info.value.issues
    assert [issue.type for issue in issues] == ["invalid_node_schema"]
    assert issues[0].node == "bad"
    assert issues[0].field == "traversal"


def test_compile_okf_release_fails_on_asymmetric_alternative(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    _write_node(
        knowledge_dir / "option-a.md",
        """---
title: Option A
group: ops
traversal: conditional
decision-domain: operating_model
alternatives: [option-b]
---

# Option A
""",
    )
    _write_node(
        knowledge_dir / "option-b.md",
        """---
title: Option B
group: ops
traversal: conditional
decision-domain: operating_model
---

# Option B
""",
    )

    with pytest.raises(OKFCompileError) as exc_info:
        compile_okf_release(knowledge_dir)

    issues = exc_info.value.issues
    assert [issue.type for issue in issues] == ["asymmetric_alternative"]
    assert issues[0].node == "option-a"
    assert issues[0].field == "typed_edges.alternatives"
    assert issues[0].target == "option-b"


def _write_node(path: Path, frontmatter_and_body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter_and_body, encoding="utf-8")
