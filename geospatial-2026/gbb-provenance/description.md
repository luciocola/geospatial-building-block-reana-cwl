# GBB Provenance conformance class (draft)

| | |
|---|---|
| Conformance class | `https://luciocola.github.io/geospatial-building-block/1.0/conf/provenance` |
| Requirements class | `https://luciocola.github.io/geospatial-building-block/1.0/req/provenance` |
| Dependencies | GBB core; GBB processing activity provenance profile; `ogc.ogc-utils.prov` |
| Status | Draft, not advertised by the kernel |

This optional class is separate from [GBB core](../gbb-core/description.md).
It profiles PROV-JSON; a JSON file named "provenance" alone is not sufficient.
The incubator register for `ogc.ogc-utils.prov` is
<https://ogcincubator.github.io/bblock-prov-schema/build/register.json>.

## Requirements

### `/req/provenance/discovery`

An implementation SHALL declare which processes satisfy this class. The
reference kernel SHALL NOT advertise the class service-wide until every
registered process satisfies it. Adding this draft to a documentation catalog
does not assert implementation conformance.

### `/req/provenance/evidence`

For each successful execution of a conforming process:

1. The results SHALL contain a named output reference to a retrievable PROV-JSON
   record with media type `application/json`.
2. The record SHALL validate against the
   [processing activity profile schema](../provenance-profile/schema/provenance-profile.schema.json),
   including date-time format checks and declared process-type references.
3. At least one activity SHALL identify the kernel job identifier and process
   identifier using `gbb:executionId` and `gbb:processId`, with `gbb` declared in
   the record's `prefix` map.
4. `used`, `wasGeneratedBy` and `wasAssociatedWith` SHALL reference existing
   entities, activities and agents. Their references SHALL describe the actual
   submitted inputs, produced outputs and execution agent.
5. The activity start time SHALL not be later than its end time.

Authentication MAY be required for retrieving the record.

### `/req/provenance/validation`

Provenance-profile validation SHALL have its own recorded result. Successful
workflow execution or an exit code of zero SHALL NOT be substituted for a
provenance validation result. Invalid provenance SHALL prevent advertising
successful provenance conformance, without misrepresenting the workflow status.

## Abstract tests and implementation status

- Validate the existing profile example with a JSON Schema validator and format
  checking; this establishes a schema fixture, not service conformance.
- For each registered process, execute a representative job, retrieve the
  declared provenance artifact through the authenticated results reference,
  and verify the schema, identities, relation targets and timestamps.
- Corrupt a required activity field or a relation target and verify that the
  provenance validation result is unsuccessful.

The imagery harmonization producers currently emit compact execution summaries,
not this profile's PROV-JSON structure. Producer normalization, job identity
wiring and recorded semantic validation remain implementation work. The core
class's `validation.passed` currently describes execution success, not successful
validation against this provenance class.

Liability claims remain a separate optional capability; they are not required
by this class.
