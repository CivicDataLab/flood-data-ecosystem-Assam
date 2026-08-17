# Risk Data Library Standard (RDLS) schema

`rdls_schema.json` is vendored from [GFDRR/rdl-standard](https://github.com/GFDRR/rdl-standard) so that
validation works offline and stays stable regardless of upstream changes.

- Schema version: **0.2.0** (per the schema's own `$id`; the upstream repo's overall project
  versioning shows 1.0, but the JSON Schema itself is still at 0.2.0 as of this pin)
- Pinned from commit: `956ce6f4cff660304e63ba74fb889708da9edd57` (`main`, 2025-12-16)
- Source: https://raw.githubusercontent.com/GFDRR/rdl-standard/main/schema/rdls_schema.json

To update, re-fetch the file above, update the commit SHA and version noted here, and re-run
`pytest Tests/test_rdls_metadata.py` — fix any new validation errors before committing.
