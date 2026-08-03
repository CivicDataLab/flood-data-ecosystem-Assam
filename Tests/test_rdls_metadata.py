"""Validate every Sources/*/metadata/*.json file against the vendored RDLS schema."""
import json

import jsonschema
import pytest

from helpers import ROOT, SOURCES, skip_if_missing

SCHEMA_PATH = ROOT / "schema" / "rdls" / "rdls_schema.json"


@pytest.fixture(scope="session")
def rdls_validator():
    skip_if_missing(SCHEMA_PATH)
    schema = json.loads(SCHEMA_PATH.read_text())
    resolver = jsonschema.validators.RefResolver.from_schema(schema)
    return jsonschema.Draft202012Validator(
        schema, resolver=resolver, format_checker=jsonschema.FormatChecker()
    )


def _rdls_files():
    return sorted(SOURCES.glob("*/metadata/*.json"))


@pytest.mark.parametrize("path", _rdls_files(), ids=lambda p: str(p.relative_to(SOURCES)))
def test_rdls_file_is_valid(rdls_validator, path):
    data = json.loads(path.read_text())
    errors = sorted(rdls_validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"  - {'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
        )
        pytest.fail(f"{path} failed RDLS schema validation:\n{details}")


def test_at_least_one_rdls_file_exists():
    assert _rdls_files(), "Expected at least one Sources/*/metadata/*.json RDLS file"
