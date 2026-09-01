import os
import json
import pytest

from backend.validation_dataset.run_validation import BASE_DIR, MANIFEST_PATH

def test_validation_dataset_manifest_integrity():
    """Verify that all 18 validation dataset files exist and manifest has ground truth."""
    assert os.path.exists(MANIFEST_PATH), "manifest.json should exist"
    
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    assert len(manifest) == 18, f"Expected 18 validation documents, found {len(manifest)}"

    for item in manifest:
        rel_path = item["filename"]
        abs_path = os.path.join(BASE_DIR, rel_path)
        assert os.path.exists(abs_path), f"Validation PDF {rel_path} does not exist"
        assert os.path.getsize(abs_path) > 100, f"Validation PDF {rel_path} is too small / corrupted"
        assert "expected_type" in item, f"Manifest item {rel_path} missing expected_type"
        assert "expected_fields" in item, f"Manifest item {rel_path} missing expected_fields"
        assert "expected_null_fields" in item, f"Manifest item {rel_path} missing expected_null_fields"
        assert "expected_extraction_method" in item, f"Manifest item {rel_path} missing expected_extraction_method"
