# Unity Data Contracts Rule Card

**Trigger:**
- Table, display key, DTO, output-shape, backend route, or response-apply work.

**Required:**
- Verify source rows, display keys, displayed text, request/response DTOs, output shape, merge rules, and response apply path.
- State whether each changed field is a delta carrier, a final snapshot, or display-only data.
- Treat arrays as shaped contracts: record length, index meaning, and merge behavior.
- Keep server-authoritative data visible. Expose contract mismatches instead of hiding them with local fallback behavior.

**Forbidden:**
- Do not stop at a single-item builder when a final aggregator or send site changes the output shape.
- Do not assume the backend recalculates values unless the actual route or service proves it.
- Do not use display fallback text as proof that the source data is valid.

**Required evidence:**
- A contract summary naming the source row or DTO, final transmitted shape, and response apply owner.
