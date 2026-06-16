from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from .contracts import validate_tool_spec_v1, validate_tool_spec_v2
from .tool_catalog import build_default_tool_registry
from .tool_registry import failed_tool_result, failed_tool_result_v2


@click.group("tools")
def tools_cmd() -> None:
    pass


@tools_cmd.command("list")
@click.option("--schema", "schema_version", default="v1")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def list_cmd(ctx, schema_version: str, as_json: bool) -> None:
    if not _valid_schema(ctx, schema_version, as_json):
        return
    registry = build_default_tool_registry(ctx.obj["config"], ctx.obj["project_path"])
    payload = registry.list_payload(schema_version)
    _emit(payload, as_json)


@tools_cmd.command("show")
@click.argument("tool_name")
@click.option("--schema", "schema_version", default="v1")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def show_cmd(ctx, tool_name: str, schema_version: str, as_json: bool) -> None:
    if not _valid_schema(ctx, schema_version, as_json):
        return
    registry = build_default_tool_registry(ctx.obj["config"], ctx.obj["project_path"])
    try:
        spec = registry.get(tool_name).spec
        if schema_version == "v2":
            payload = validate_tool_spec_v2(spec.to_payload_v2())
        else:
            payload = validate_tool_spec_v1(spec.to_payload())
    except KeyError as exc:
        if schema_version == "v2":
            _emit(failed_tool_result_v2(tool_name, "read", str(exc)), as_json)
        else:
            _emit(failed_tool_result(tool_name, "planned", str(exc)), as_json)
        ctx.exit(2)
        return
    _emit(payload, as_json)


@tools_cmd.command("call")
@click.argument("tool_name")
@click.option("--schema", "schema_version", default="v1")
@click.option("--payload-json", default=None, help="Tool input JSON object.")
@click.option(
    "--payload-file",
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    default=None,
    help="Path to a JSON object payload.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def call_cmd(
    ctx,
    tool_name: str,
    schema_version: str,
    payload_json: str | None,
    payload_file: str | None,
    as_json: bool,
) -> None:
    if not _valid_schema(ctx, schema_version, as_json):
        return
    registry = build_default_tool_registry(ctx.obj["config"], ctx.obj["project_path"])
    try:
        payload = _load_payload(payload_json, payload_file)
        result = registry.call(tool_name, payload, schema_version)
    except (json.JSONDecodeError, ValueError) as exc:
        if schema_version == "v2":
            result = failed_tool_result_v2(tool_name, "read", str(exc))
        else:
            result = failed_tool_result(tool_name, "planned", str(exc))
        _emit(result, as_json)
        ctx.exit(2)
        return
    except KeyError as exc:
        if schema_version == "v2":
            result = failed_tool_result_v2(tool_name, "read", str(exc))
        else:
            result = failed_tool_result(tool_name, "planned", str(exc))
        _emit(result, as_json)
        ctx.exit(2)
        return
    _emit(result, as_json)


def _load_payload(payload_json: str | None, payload_file: str | None) -> dict[str, Any]:
    if payload_json and payload_file:
        raise ValueError("provide only one of --payload-json or --payload-file")
    if payload_file:
        loaded = json.loads(Path(payload_file).read_text(encoding="utf-8"))
    elif payload_json:
        loaded = json.loads(payload_json)
    else:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ValueError("payload must be a JSON object")
    return loaded


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(payload)


def _valid_schema(ctx, schema_version: str, as_json: bool) -> bool:
    if schema_version in {"v1", "v2"}:
        return True
    _emit(failed_tool_result("tools", "planned", f"unsupported schema: {schema_version}"), as_json)
    ctx.exit(2)
    return False
