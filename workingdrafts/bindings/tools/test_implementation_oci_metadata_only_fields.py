"""Independent OCI field-plane regressions for metadata-only Resource models."""

import copy
import tempfile
import unittest

from workingdrafts.bindings.tools import oci_examples as oci


class OciMetadataOnlyFields(unittest.TestCase):
    version = "/dirs/main/notes/info/versions/v1"

    @staticmethod
    def records(values):
        records, documents = oci.sample_records()
        root = next(record for record in records if record["kind"] == "registry")
        for model in (root["modelresolved"], root["entity"]["modelsource"], root["entity"]["model"]):
            definitions = model["groups"]["dirs"]["resources"]["notes"].setdefault("attributes", {})
            for name in values:
                definitions[name] = {"type": "any"}
        version = next(record for record in records if record["entity"]["xid"] == OciMetadataOnlyFields.version)
        version["entity"].update(copy.deepcopy(values))
        return records, documents

    def round_trip(self, values):
        records, documents = self.records(values)
        with tempfile.TemporaryDirectory(prefix="oci-field-plane-") as folder:
            root = oci.build_layout(folder, records, documents, reference="ordinary", page_size=2)
            validation = oci.validate_layout(folder, "ordinary")
            self.assertEqual(validation["root"], root["digest"])
            result = oci.lookup_layout(folder, self.version, reference="ordinary")
            for name, value in values.items():
                self.assertIn(name, result["value"])
                self.assertEqual(result["value"][name], value)
            with self.assertRaises(oci.FederationError) as error:
                oci.lookup_layout(folder, self.version, reference="ordinary", operation="document")
            self.assertEqual(error.exception.code, "unsupported_operation")

    def test_ordinary_names_remain_metadata_not_documents_or_locators(self):
        self.round_trip({
            "note": {"nested": None, "value": 42},
            "notebase64": "not a document encoding",
            "noteurl": "https://must-not-fetch.invalid/blob",
        })

    def test_explicit_null_metadata_survives_full_closure_and_lookup(self):
        self.round_trip({"note": None, "notebase64": None, "noteurl": None})

    def test_document_capable_versions_keep_detached_field_restrictions(self):
        self.reject_document_field("file")

    def test_document_capable_versions_reject_inline_base64(self):
        self.reject_document_field("filebase64")

    def test_document_capable_versions_reject_conflicting_url(self):
        self.reject_document_field("fileurl")

    def reject_document_field(self, field):
        records, documents = oci.sample_records()
        version = next(record for record in records
                       if record["entity"]["xid"] == "/dirs/main/files/sample/versions/v1")
        version["entity"][field] = "https://must-not-fetch.invalid/document"
        with tempfile.TemporaryDirectory(prefix="oci-field-plane-control-") as folder:
            with self.assertRaises(oci.FederationError) as error:
                oci.build_layout(folder, records, documents)
            self.assertEqual(error.exception.code, "invalid_package")
