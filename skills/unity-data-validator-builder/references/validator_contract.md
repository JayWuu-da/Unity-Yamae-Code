# Validator Contract

A generated validator checks data contracts from source rows to final evidence reports. Keep project-specific names in the generated profile.

## Contract Layers
- Source table rows: required sections, required fields, and row identifiers.
- Lookup links: field-to-field references between table sections.
- Relationship targets: referenced rows that must exist.
- Display key links: display keys that must resolve in configured source data unless explicitly marked as sentinel values.
- Output shape notes: fields, index meaning, and array shape assumptions documented in the profile.
- Read-only server comparison: route, DTO, or response fields may be named in the generated profile, but the validator must not modify server code.

## Report Requirements
- Markdown report for humans.
- JSON report for automated checks.
- Each issue should include severity, source table, row id, field, and a concise message.
- A passing report must still state how many tables and relationships were checked.

## Failure Policy
Missing data should fail loudly. Do not add fallback values to make the report pass.
