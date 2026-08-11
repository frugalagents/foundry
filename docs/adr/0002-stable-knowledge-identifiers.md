# ADR 0002: Stable Knowledge Identifiers

**Status:** Accepted
**Date:** 2026-08-11
**Decision owners:** Knowledge model maintainers

## Context

Knowledge identifiers will be referenced by claims, relationships, decision
patterns, catalog releases, customer revisions, and historical outcomes.
Changing or deleting an identifier can therefore make prior decisions
unreplayable.

## Decision

Published identifiers are immutable, globally unique within the knowledge
repository, and never reused.

Identifiers use a namespaced form:

```text
<kind>:<stable-slug>
```

Examples include `capability:model-routing`, `offering:managed-runtime`, and
`claim:runtime-supports-mcp`.

Display titles, product names, and descriptions may change without changing the
identifier. Formatting differences or marketing renames are not sufficient
reasons to create a new identity.

## Identity Changes

Every identity change is an approved `IdentifierTransition`:

| Change | Prior IDs | Successor IDs | Required behavior |
|---|---:|---:|---|
| Rename | 1 | 1 | Old ID becomes an alias of the successor |
| Merge | 2 or more | 1 | All prior IDs resolve to the successor |
| Split | 1 | 2 or more | Requires explicit contextual remapping |
| Retire | 1 | 0 | ID remains resolvable as retired |

Aliases are historical identifiers, not search synonyms. An entity may not
alias its own ID, and an alias may resolve to only one active entity. Split
transitions cannot be resolved automatically without context.

`SUPERSEDES` is a semantic relationship between two distinct entities or
versions. It does not rewrite either identifier.

## Deletion

Published entities, relationships, claims, and transitions are never physically
deleted from release history. They are deprecated or retired. Draft records
that have never appeared in a catalog release may be removed through normal
review.

## Compiler Requirements

The knowledge compiler must fail when:

- an identifier or alias is reused;
- an alias chain contains a cycle;
- a rename, merge, split, or retirement has an invalid shape;
- an identity transition is not approved;
- a reference resolves to multiple active entities;
- a retired ID is used as a new identity; or
- a split reference lacks an explicit successor selection.

Catalog releases preserve the authored identifiers and accepted transition map
used during compilation so historical customer revisions remain replayable.
