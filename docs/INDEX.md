# Documentation

The repository README is the product-facing entry point. The files in this
directory explain development, product direction, implementation boundaries,
and planned behavior.

## Start here

| If you want to… | Read… |
|---|---|
| Use or evaluate ObjectSnip | [`../README.md`](../README.md) |
| Set up the project or run checks | [`DEVELOPMENT.md`](DEVELOPMENT.md) |
| Understand the product and its boundaries | [`PRODUCT.md`](PRODUCT.md) |
| See what exists and what comes next | [`ROADMAP.md`](ROADMAP.md) |
| Understand the code structure | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Work on capture behavior | [`features/capture.md`](features/capture.md) |
| Work on object selection | [`features/selection.md`](features/selection.md) |
| Work on clipboard or file output | [`features/export.md`](features/export.md) |
| Work on the SAM backend | [`SAM2.md`](SAM2.md) |
| Understand a durable technical choice | [`decisions/`](decisions/README.md) |

## Document roles

- `PRODUCT.md` describes who the product is for and what belongs in it.
- `ROADMAP.md` records implementation status and sequencing.
- Feature documents describe intended user-visible behavior. They may include
  planned behavior that has not been implemented yet.
- `ARCHITECTURE.md` describes the current structure and important boundaries.
- Decision records preserve the reasoning behind costly technical choices.
- Code and tests are authoritative for what is implemented today.

When implementation changes, update the smallest owning document. Avoid
copying the same requirement or setup instructions into multiple files.
