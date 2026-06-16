# Unity Data Validator

Domain: `{{DOMAIN}}`

This validator reads Unity table data from the project path supplied at runtime:

```text
{{PROJECT_PATH}}
```

Configure project-specific table roots, table files, sections, fields, and relationships in
`profiles/{{DOMAIN}}.yaml` before running the validator.
Reports are emitted as Markdown and JSON under `reports/`.

Run:

```bash
python src/validator.py \
  --project <unity-project-root> \
  --profile profiles/{{DOMAIN}}.yaml \
  --report-md reports/{{DOMAIN}}.md \
  --report-json reports/{{DOMAIN}}.json
```
