import json
from pathlib import Path
from typing import Any

import click

from .contracts import validate_integration_doctor_v1

DESKTOP_INTEGRATIONS = {
    "codex-app": {
        "entrypoint": ".agents/skills/k-unity-yamae/SKILL.md",
        "guidance": (
            "Open the Unity project folder in Codex App; Codex reads AGENTS.md "
            "and repo skills."
        ),
    },
    "codex-cli": {
        "entrypoint": ".agents/skills/k-unity-yamae/SKILL.md",
        "guidance": "Run Codex CLI from the Unity project root so AGENTS.md and repo skills apply.",
    },
    "claude-code-desktop": {
        "entrypoint": ".claude/skills/k-unity-yamae/SKILL.md",
        "guidance": "Open the Unity project in Claude Code Desktop with Git for Windows available.",
    },
    "claude-cli": {
        "entrypoint": ".claude/commands/kunity-yamae.md",
        "guidance": "Run Claude CLI from the Unity project root and invoke /k-unity-yamae.",
    },
}


@click.group("providers")
def providers_cmd() -> None:
    pass


@providers_cmd.command("doctor")
@click.argument("integration", required=False)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def provider_doctor_cmd(ctx, integration: str | None, as_json: bool) -> None:
    project_path: Path = ctx.obj["project_path"]
    payload = build_provider_doctor(
        ctx.obj["config"],
        provider=integration,
        project_path=project_path,
    )

    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        for name, status in payload["integrations"].items():
            click.echo(f"{name}: {status['status']} ({status['entrypoint']})")
        for name, status in payload["offline_handoffs"].items():
            click.echo(f"{name}: {status['status']} ({status['usage']})")

    if integration is not None and _single_integration_has_blocker(payload):
        ctx.exit(2)


def build_provider_doctor(
    config: dict[str, Any],
    *,
    provider: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    del config
    root = project_path or Path.cwd()
    integrations = _selected_integrations(root, provider)
    payload = {
        "schema": "unity-harness.desktop-integration-doctor.v1",
        "integrations": integrations,
        "offline_handoffs": _offline_handoffs(provider),
    }
    return validate_integration_doctor_v1(payload)


def _selected_integrations(root: Path, provider: str | None) -> dict[str, Any]:
    if provider == "local-patch":
        return {}
    if provider is not None and provider not in DESKTOP_INTEGRATIONS:
        raise click.ClickException(f"Unknown desktop integration: {provider}")

    names = [provider] if provider else list(DESKTOP_INTEGRATIONS)
    return {
        name: _integration_status(root, name, DESKTOP_INTEGRATIONS[name])
        for name in names
        if name is not None
    }


def _integration_status(root: Path, name: str, spec: dict[str, str]) -> dict[str, Any]:
    entrypoint = spec["entrypoint"]
    exists = (root / entrypoint).exists()
    return {
        "kind": "desktop-cli",
        "entrypoint": entrypoint,
        "status": "ready" if exists else "not_installed",
        "guidance": spec["guidance"],
        "usage": _integration_usage(name),
    }


def _integration_usage(name: str) -> str:
    usages = {
        "codex-app": "Open the project folder in Codex App.",
        "codex-cli": "Run codex from the project root.",
        "claude-code-desktop": "Open the project folder in Claude Code Desktop.",
        "claude-cli": "Run claude from the project root, then invoke /k-unity-yamae.",
    }
    return usages[name]


def _offline_handoffs(provider: str | None = None) -> dict[str, Any]:
    if provider is not None and provider != "local-patch":
        return {}
    return {
        "local-patch": {
            "status": "ready",
            "usage": (
                'kunity-yamae run --agent local-patch "$TASK" '
                "--patch-file proposed.diff --guarded-agent-patch --json"
            ),
        }
    }


def _single_integration_has_blocker(payload: dict[str, Any]) -> bool:
    return provider_doctor_status(payload) != "ready"


def provider_doctor_status(payload: dict[str, Any]) -> str:
    if payload["integrations"]:
        return next(iter(payload["integrations"].values()))["status"]
    return next(iter(payload["offline_handoffs"].values()))["status"]
