# Geometry-Indexed Domain Pack Standard v1.0

Status: v0.3.0 method-freeze candidate. This standard extends, and does not overwrite, the one-dimensional TLD v2.1 input protocol.

## Purpose and authority

A geometry-indexed domain pack is the custody and translation boundary for a field assay. It preserves the coordinates, components, masks, boundaries, acquisition identities, independent-parent structure, and registered transformations needed to decide whether two calculations refer to the same scientific object.

The authoritative machine contract is `geometry-indexed-domain-pack/v1.schema.json`. Supporting records use the other geometry v1 schemas. A pack is invalid when a required identity is missing or when any referenced registry changes after freeze.

## Supported kinds

- `SEQUENCE_1D`
- `SCALAR_FIELD_2D`
- `VECTOR_FIELD_2D`
- `SCALAR_VOLUME_3D`
- `VECTOR_VOLUME_3D`
- `SPATIOTEMPORAL_SCALAR_FIELD`
- `SPATIOTEMPORAL_VECTOR_FIELD`
- `POINT_CLOUD`
- `MANIFOLD_SAMPLES`
- `GRAPH_GEOMETRY`
- `CORRELATION_GEOMETRY`
- `MULTIMODAL_COUPLED_FIELD`

`MULTIMODAL_COUPLED_FIELD` is not automatically ToT-BROT. That term additionally requires explicit inter-system invariants, matched null tests, and independent verification.

## Required custody

Every pack records a stable source identifier and URL, license, raw-source SHA-256 values, acquisition and canonicalization identities, coordinate system, axis names and units, orientation, grid regularity, sampling intervals, time coordinate where present, boundary conditions, periodicity, mask and missing-data semantics, components and field units, independent-parent and nested-replicate keys, experimental run and condition keys, projection/null/perturbation registry identities, domain baseline, claim ceiling, and known limitations.

An absolute local filesystem path is not a stable source identity. Raw hashes identify bytes; acquisition identity identifies the scientific collection; canonicalization identity identifies the deterministic translation.

## Parent and replicate rule

The experimental unit is the registered independent parent, not the number of pixels, voxels, time samples, projections, null children, or repeated measurements. Nested replicates remain nested. Effective-parent support must be audited before closure or emergence is computed.

## No silent flattening

A raw field may not be flattened into a vector unless a projection was registered before outcomes and includes:

1. a physical or mathematical justification;
2. a coordinate-order contract;
3. invertibility or an explicit information-loss statement;
4. compatible null families; and
5. an independent faithful representation check.

Row-major serialization by convenience is not a scientific projection.

## Eligibility

GeometryScoutV1 runs before closure. Missing coordinates, unresolved units, invalid masks, constant or degenerate observations, incomplete nulls, insufficient independent parents, insufficient support, or an applicable failed sensitivity gate make closure unauthorized. The status is `INELIGIBLE` or `INCONCLUSIVE`; it is not a negative TLD result.

No universal materialization fraction, including 21.43%, is a pass threshold. Support requirements are registered and calibrated for the domain.

## Versioning and migration

Schema version `1.0.0` is immutable. Additive optional clarifications require a new minor schema; changed meaning, required fields, identifiers, parent semantics, or canonicalization require a new major schema. Historical v2.1 sequence packs remain v2.1 records. A v2.1 pack migrates only through an explicit migration receipt that preserves its source bytes, row order, sequence operator, and historical claim boundary.

Changing a field kind, coordinate frame, mask, projection, null family, perturbation, parent key, or baseline after freeze creates a different assay. It cannot be described as a metadata correction.
