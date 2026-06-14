# Contributing

## Workflow

1. Create a branch from `master`.
2. Make focused changes with tests or documentation updates when behavior changes.
3. Run the local checks:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```

4. Open a pull request.

Direct pushes to `master` are blocked. Pull requests require review, passing CI, and code owner review for owned paths.

## Agent Artifact Hygiene

Do not commit `.omo/`, `.omx/`, `plans/`, `evidence/`, local scratch drafts, or private Unity project data unless the user explicitly asks for that artifact. The repository should stay focused on the AI-agent Unity harness source, generated entrypoint templates, tests, and maintained docs.

## Release Source

GitHub Releases and source installs are installation sources for agents and maintainers. A fresh agent can clone the git URL, run `python -m pip install -e .`, and then operate from the target Unity project root.

## Security

Do not include secrets, tokens, Unity license files, or private project data in commits, issues, logs, screenshots, or pull requests.
