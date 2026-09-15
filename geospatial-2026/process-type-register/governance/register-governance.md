# Process-Type Register Governance (ISO 19135 Oriented)

## Scope

This governance model covers lifecycle management of process-type terms used by OSPD 2026 provenance profiles.

## Roles

- Register owner: OGC-hosted governance authority.
- Control body: review board validating term quality and external mappings.
- Submitter: participant proposing new or updated terms.

## Lifecycle States

- `proposed`
- `valid`
- `superseded`
- `deprecated`
- `retired`

## Required Fields per Entry

- Stable identifier URI
- Preferred label
- Definition
- Status
- Version metadata
- At least one example usage

## Change Process

1. Submit proposal with rationale and evidence.
2. Run validation checks (identifier, schema, mapping relation integrity).
3. Control body review and decision.
4. Publish new version and changelog entry.
5. Mark supersession links for replaced entries.

## Federation Rules

Allowed relation types:

- `exactMatch`
- `closeMatch`
- `broader`
- `narrower`

All mappings must include source URI, target URI, relation type, and vocabulary source.
