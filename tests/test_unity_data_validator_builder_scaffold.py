import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/unity-data-validator-builder/scripts/scaffold_validator.py")


def run_scaffold(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=False,
        encoding="utf-8",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def create_neutral_tables(project_path: Path) -> None:
    table_root = project_path / "Assets" / "Data" / "NeutralTables"
    write_json(
        table_root / "Primary.json",
        {
            "Primary": [
                {"ID": "1", "TARGET_ID": "100", "GROUP_ID": "10", "LABEL_KEY": "label_alpha"},
                {"ID": "2", "TARGET_ID": "101", "GROUP_ID": "10", "LABEL_KEY": "label_alpha"},
            ],
            "Secondary": [{"ID": "100", "TYPE": "10", "REFERENCE_ID": "reference_100"}],
            "Grouped": [
                {"ID": "1", "GROUP_ID": "10", "ORDER": "1", "TARGET_ID": "500"},
                {"ID": "2", "GROUP_ID": "10", "ORDER": "2", "TARGET_ID": "501"},
            ],
        },
    )
    write_json(
        table_root / "Fallback.json",
        {
            "Fallback": [
                {"ID": "100", "external_id": "external-100", "KIND": "Primary"},
                {"ID": "101", "external_id": "external-101", "KIND": "Primary"},
                {"ID": "200", "external_id": None, "KIND": "Secondary"},
            ]
        },
    )
    write_json(
        table_root / "Target.json",
        {
            "Target": [
                {"ID": "1", "TARGET_ID": "500", "TYPE": "1", "VALUE": "10", "COUNT": "1"},
                {"ID": "2", "TARGET_ID": "501", "TYPE": "2", "VALUE": "20", "COUNT": "1"},
            ]
        },
    )
    write_json(
        table_root / "Labels.json",
        {"Labels": [{"ID": "1", "TEXT": "label_alpha", "KO": "알파", "EN": "Alpha"}]},
    )


def write_neutral_profile(output_path: Path) -> None:
    (output_path / "profiles" / "neutral-domain.yaml").write_text(
        "\n".join(
            [
                "domain: neutral-domain",
                "table_root: Assets/Data/NeutralTables",
                "tables:",
                "  - file: Primary.json",
                "    section: Primary",
                "    id_field: ID",
                "    required_fields: [ID, TARGET_ID, GROUP_ID, LABEL_KEY]",
                "  - file: Primary.json",
                "    section: Secondary",
                "    id_field: ID",
                "    required_fields: [ID, TYPE, REFERENCE_ID]",
                "  - file: Primary.json",
                "    section: Grouped",
                "    id_field: ID",
                "    required_fields: [ID, GROUP_ID, ORDER, TARGET_ID]",
                "  - file: Fallback.json",
                "    section: Fallback",
                "    id_field: ID",
                "    where: {field: KIND, equals: Primary}",
                "    required_fields: [ID, external_id, KIND]",
                "  - file: Target.json",
                "    section: Target",
                "    id_field: ID",
                "    required_fields: [ID, TARGET_ID, TYPE, VALUE, COUNT]",
                "  - file: Labels.json",
                "    section: \"*\"",
                "    id_field: ID",
                "    required_fields: [TEXT]",
                "relationships:",
                "  - name: primary-target",
                "    from: {file: Primary.json, section: Primary, field: TARGET_ID}",
                "    to_any:",
                "      - {file: Primary.json, section: Secondary, field: ID}",
                "      - {file: Fallback.json, section: Fallback, field: ID}",
                "    skip_values: [\"\", \"0\", \"none\", \"-1\"]",
                "  - name: primary-group",
                "    from: {file: Primary.json, section: Primary, field: GROUP_ID}",
                "    to: {file: Primary.json, section: Grouped, field: GROUP_ID}",
                "    skip_values: [\"\", \"0\", \"none\", \"-1\"]",
                "  - name: primary-label",
                "    from: {file: Primary.json, section: Primary, field: LABEL_KEY}",
                "    to: {file: Labels.json, section: \"*\", field: TEXT}",
                "    skip_values: [\"\", \"0\", \"none\", \"-1\"]",
                "  - name: grouped-target",
                "    from: {file: Primary.json, section: Grouped, field: TARGET_ID}",
                "    to: {file: Target.json, section: Target, field: TARGET_ID}",
                "    skip_values: [\"\", \"0\", \"none\", \"-1\"]",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_generated_validator(
    output_path: Path,
    project_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(output_path / "src" / "validator.py"),
            "--project",
            str(project_path),
            "--profile",
            str(output_path / "profiles" / "neutral-domain.yaml"),
            "--report-md",
            str(output_path / "reports" / "neutral-domain.md"),
            "--report-json",
            str(output_path / "reports" / "neutral-domain.json"),
        ],
        check=False,
        encoding="utf-8",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


def test_scaffold_creates_generic_validator_project_and_validates_configured_tables(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = tmp_path / "GeneratedValidator"
    create_neutral_tables(project_path)

    scaffold = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "neutral-domain",
        "--output",
        str(output_path),
    )

    assert scaffold.returncode == 0, scaffold.stderr
    assert (output_path / "README.md").exists()
    assert (output_path / "profiles" / "neutral-domain.yaml").exists()
    assert (output_path / "src" / "validator.py").exists()
    assert (output_path / "tests" / "test_validator_contract.py").exists()
    assert (output_path / "reports" / ".gitkeep").exists()

    write_neutral_profile(output_path)
    result = run_generated_validator(output_path, project_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(
        (output_path / "reports" / "neutral-domain.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "passed"
    assert report["summary"]["checked_tables"] == 6
    assert report["summary"]["checked_relationships"] >= 4


def test_scaffold_rejects_unsafe_domain_name(tmp_path: Path) -> None:
    result = run_scaffold(
        "--project",
        str(tmp_path / "UnityProject"),
        "--domain",
        "../bad",
        "--output",
        str(tmp_path / "GeneratedValidator"),
    )

    assert result.returncode != 0
    assert "domain" in result.stderr
    assert "safe" in result.stderr
    assert not (tmp_path / "GeneratedValidator").exists()


def test_scaffold_refuses_existing_output_without_force(tmp_path: Path) -> None:
    output_path = tmp_path / "GeneratedValidator"
    output_path.mkdir()
    marker = output_path / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    result = run_scaffold(
        "--project",
        str(tmp_path / "UnityProject"),
        "--domain",
        "neutral-domain",
        "--output",
        str(output_path),
    )

    assert result.returncode != 0
    assert "--force" in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep"


def test_scaffold_force_refuses_project_root_output(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    marker = project_path / "ProjectSettings" / "ProjectVersion.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("m_EditorVersion: 6000.0.0f1", encoding="utf-8")

    result = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "neutral-domain",
        "--output",
        str(project_path),
        "--force",
    )

    assert result.returncode != 0
    assert "output" in result.stderr
    assert marker.read_text(encoding="utf-8") == "m_EditorVersion: 6000.0.0f1"


def test_scaffold_force_refuses_project_child_output(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = project_path / "Assets" / "GeneratedValidator"
    marker = output_path / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("keep", encoding="utf-8")

    result = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "neutral-domain",
        "--output",
        str(output_path),
        "--force",
    )

    assert result.returncode != 0
    assert "output" in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (output_path / "src" / "validator.py").exists()


def test_generated_validator_reports_missing_relationship(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = tmp_path / "GeneratedValidator"
    create_neutral_tables(project_path)
    primary_path = project_path / "Assets" / "Data" / "NeutralTables" / "Primary.json"
    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    primary["Primary"][0]["TARGET_ID"] = "999"
    primary_path.write_text(json.dumps(primary), encoding="utf-8")
    scaffold = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "neutral-domain",
        "--output",
        str(output_path),
    )
    assert scaffold.returncode == 0, scaffold.stderr

    write_neutral_profile(output_path)
    result = run_generated_validator(output_path, project_path)

    assert result.returncode != 0
    report = json.loads(
        (output_path / "reports" / "neutral-domain.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "failed"
    assert any("TARGET_ID" in issue["message"] for issue in report["issues"])


def test_skill_files_do_not_contain_project_specific_examples() -> None:
    skill_root = Path("skills/unity-data-validator-builder")
    if not skill_root.exists():
        return
    banned_patterns = ["D:/", "C:/", "profiles/project-", "project-specific-example"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in skill_root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".py", ".yaml"}
    )

    found = [pattern for pattern in banned_patterns if pattern in text]

    assert found == []
