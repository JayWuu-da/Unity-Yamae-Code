import re
from pathlib import Path


def test_korean_readme_is_agent_handoff_not_human_command_manual() -> None:
    readme = Path("README_KO.md").read_text(encoding="utf-8")

    assert "## 주요 명령어" not in readme
    assert "/path/to/UnityProject" not in readme
    assert "/path/to/your/unity/project" not in readme
    assert re.search(r"kunity-yamae\s+\w+\s+--project", readme) is None
    assert "모든 Unity 프로젝트를 이해" not in readme
    assert "AI 에이전트용 Unity 하네스" in readme
    assert "git URL" in readme
    assert "현재 Unity 프로젝트 루트" in readme


def test_korean_readme_states_discovered_fact_limits() -> None:
    readme = Path("README_KO.md").read_text(encoding="utf-8")

    assert re.search(r"발견된 파일|발견된 사실", readme)
    assert re.search(r"editor-probe|에디터 프로브", readme)
