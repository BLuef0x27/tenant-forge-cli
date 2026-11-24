"""Tests for tenant_forge.generator validation and tfvars generation."""

from pathlib import Path

import pytest

from tenant_forge.generator import (
    validate_cidr,
    validate_environment,
    validate_tenant_id,
    write_tfvars,
)


def test_valid_tenant_id_normalizes_case_and_whitespace():
    assert validate_tenant_id("  Acme-Corp ") == "acme-corp"
    assert validate_tenant_id("ACME") == "acme"
    assert validate_tenant_id("tenant-01") == "tenant-01"


def test_tenant_id_rejects_invalid_special_characters():
    for bad in ["acme_corp", "acme corp", "acme.corp", "acme/corp", "acme$prox", ""]:
        with pytest.raises(ValueError):
            validate_tenant_id(bad)


def test_cidr_accepts_supported_prefixes():
    assert validate_cidr("10.20.0.0/16") == "10.20.0.0/16"
    assert validate_cidr("10.20.5.0/24") == "10.20.5.0/24"


def test_cidr_rejects_slash_eight_blocks():
    with pytest.raises(ValueError):
        validate_cidr("10.0.0.0/8")


def test_cidr_rejects_too_narrow_and_malformed_values():
    with pytest.raises(ValueError):
        validate_cidr("10.20.0.0/25")
    with pytest.raises(ValueError):
        validate_cidr("not-a-cidr")


def test_environment_validation():
    assert validate_environment(" Staging ") == "staging"
    assert validate_environment("PROD") == "prod"
    with pytest.raises(ValueError):
        validate_environment("dev")


def test_write_tfvars_creates_expected_file(tmp_path: Path):
    out = write_tfvars("Acme-Corp", "staging", "10.20.0.0/16", output_dir=tmp_path / "tenants")
    assert out == tmp_path / "tenants" / "acme-corp-staging.tfvars"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert 'tenant_id   = "acme-corp"' in content
    assert 'environment = "staging"' in content
    assert 'vpc_cidr    = "10.20.0.0/16"' in content


def test_write_tfvars_rejects_bad_cidr_and_writes_nothing(tmp_path: Path):
    with pytest.raises(ValueError):
        write_tfvars("acme", "staging", "10.0.0.0/8", output_dir=tmp_path)
    assert not (tmp_path / "acme-staging.tfvars").exists()


def test_write_tfvars_rejects_bad_environment(tmp_path: Path):
    with pytest.raises(ValueError):
        write_tfvars("acme", "dev", "10.20.0.0/16", output_dir=tmp_path)
    assert not (tmp_path / "acme-dev.tfvars").exists()
