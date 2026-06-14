import re
from pathlib import Path


def test_architecture_docs_center_agent_harness_and_static_limits() -> None:
    docs = "\n".join(
        [
            Path("docs/ANALYSIS.md").read_text(encoding="utf-8"),
            Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8"),
        ]
    )

    assert "AI-agent Unity harness" in docs
    assert "target Unity project root" in docs
    assert re.search(r"discovered static facts|static facts|signals", docs)
    assert re.search(r"editor-probe|Editor probe", docs)
    assert not re.search(
        r"general CLI product|understands every Unity project|complete object graph",
        docs,
        flags=re.IGNORECASE,
    )
