# Documentation index

This page is the entry point for humans and coding agents. Read only the
smallest relevant set below; follow links when a task crosses a boundary.

## Sources of truth

| Subject | Authoritative source |
|---|---|
| Product purpose, principles, scope, non-goals | [`PRODUCT.md`](PRODUCT.md) |
| System boundaries, dependency rules, technical invariants | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Current milestone, sequencing, project status | [`ROADMAP.md`](ROADMAP.md) |
| Selection interaction and prompts | [`features/selection.md`](features/selection.md) |
| SAM 2 backend contract and setup | [`SAM2.md`](SAM2.md) |
| Screen capture and frozen overlay | [`features/capture.md`](features/capture.md) |
| Clipboard and file output | [`features/export.md`](features/export.md) |
| Reasons for consequential technical choices | [`decisions/`](decisions/README.md) |
| Implemented behavior | Tests and code |

If two live documents conflict, the document that owns the subject in this
table wins. Fix the non-owning reference rather than copying the requirement.

## Minimal context by task

| Task | Read first |
|---|---|
| Change selection behavior | `PRODUCT.md`, `features/selection.md`, relevant domain/UI code and tests |
| Change screenshot behavior | `PRODUCT.md`, `features/capture.md`, relevant capture/UI code and tests |
| Change clipboard or saved output | `PRODUCT.md`, `features/export.md`, relevant export code and tests |
| Change session state or dependency direction | `ARCHITECTURE.md`, affected feature file, relevant code and tests |
| Add or compare a segmentation backend | `ARCHITECTURE.md`, `ROADMAP.md`, `SAM2.md`, segmentation interface and benchmarks |
| Choose the next work item | `PRODUCT.md`, `ROADMAP.md` |
| Reconsider a foundational choice | Relevant live document and decision records |

## Document status

- **Draft**: proposed and explicitly open to revision; not yet accepted.
- **Accepted**: intended behavior or direction.
- **Implemented**: present in code but not necessarily fully verified.
- **Verified**: implemented with appropriate automated or manual evidence.
- **Deferred**: intentionally outside the active milestone.

Status applies at the smallest clearly labelled scope. Unlabelled content in a
Draft document is Draft.

## Change protocol

1. Change the owning feature specification and its acceptance criteria.
2. Change or add tests that express the new behavior.
3. Change the implementation.
4. Update `ARCHITECTURE.md` only if a boundary or invariant changed.
5. Update `ROADMAP.md` only if milestone scope or status changed.
6. Add a decision record only for a consequential choice whose rationale will
   matter later.

Do not maintain prose changelogs or duplicate acceptance criteria. Git preserves
history; live documents describe the current intended state.

## Coding-agent working agreement

For a scoped implementation task:

1. Name the feature or acceptance criterion being changed.
2. Read only its minimal context set from this index.
3. Inspect relevant code and tests before proposing files.
4. State the intended file impact before editing.
5. Do not implement later milestones opportunistically.
6. Ask before editing files, as required by the repository instructions.
7. Report specification ambiguity rather than inventing durable product policy.
