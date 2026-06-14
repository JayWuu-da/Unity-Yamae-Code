from pathlib import Path

import click


def with_local_patch_file(config: dict, agent_name: str, patch_file: str) -> dict:
    if agent_name != "local-patch":
        raise click.ClickException("--patch-file is only supported with --agent local-patch")
    patched_config = dict(config)
    agents_config = dict(patched_config.get("agents", {}))
    backends = dict(agents_config.get("backends", {}))
    local_patch = dict(backends.get("local-patch", {}))
    local_patch["patch_file"] = str(Path(patch_file).resolve())
    backends["local-patch"] = local_patch
    agents_config["backends"] = backends
    patched_config["agents"] = agents_config
    return patched_config
