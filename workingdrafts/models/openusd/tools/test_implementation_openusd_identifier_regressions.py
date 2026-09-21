"""Focused guards for the OpenUSD symbolic-ID assignment/resolution contract.

Run with the standard library:
    python -m workingdrafts.models.openusd.tools.test_implementation_openusd_identifier_regressions

OPENUSD_IDENTIFIER_SPEC selects an explicit source copy for reproducible red/green
evidence. These tests guard normative prose and independently verified examples;
they do not claim to execute a host implementation or validate its whole model.
"""

import hashlib
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get(
    "OPENUSD_IDENTIFIER_SPEC",
    ROOT / "spec.md",
))


class OpenUsdIdentifierRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_text(encoding="utf-8")
        cls.text = " ".join(cls.raw.split())
        cls.construction = cls.text.split(
            "#### 5.1.1. The Symbolic Identifier Construction", 1
        )[1].split("### 5.2.", 1)[0]

    def test_candidate_construction_and_published_examples_are_unchanged(self):
        for clause in (
            "Reverse the authority's `.`-separated labels",
            "Percent-decode each path segment and discard the empty ones.",
            "Letter case is preserved.",
            "If the result is longer than 128 characters",
            "drop trailing labels",
            "the UTF-8 encoding of the **exact source string**",
        ):
            self.assertIn(clause, self.construction)
        for row in (
            "| `@./pump.usda@` | `pump.usda` | `pump.usda` | `pump.usda` |",
            "| `@textures/albedo.png@` | `textures/albedo.png` | "
            "`textures.albedo.png` | `textures/albedo.png` |",
            "| `@pkg.usdz[tex/a.png]@` | `pkg.usdz[tex/a.png]` | "
            "`pkg.usdz-tex.a.png` | `pkg.usdz[tex/a.png]` |",
        ):
            self.assertIn(row, self.construction)

    def test_collision_only_long_candidates_reserve_the_suffix(self):
        self.assertEqual(119 + 1 + 8, 128)
        self.assertGreater(120 + 1 + 8, 128)
        self.assertGreater(128 + 1 + 8, 128)
        self.assertIn(
            "including collision-only results of 120 through 128 characters",
            self.construction,
        )
        self.assertIn("at most 119 characters before adding the suffix", self.construction)
        self.assertIn("same normalized source labels", self.construction)
        self.assertIn("MUST NOT split a normalized label again at its literal dots", self.construction)

    def test_assignment_is_state_aware_and_preserves_published_bindings(self):
        for clause in (
            "deterministic for a fixed sibling state",
            "MUST retain an existing binding for the same exact source",
            "MUST NOT rename an existing entity",
            "MUST NOT rebind an existing ID to another source",
            "even if the sibling that caused the collision is later deleted",
            "Inconsistent bindings MUST be rejected rather than repaired by renaming",
            "legal Core container IDs remain verbatim",
        ):
            self.assertIn(clause, self.text)
        self.assertNotIn(
            "a Producer and a Consumer agree without a lookup table",
            self.construction,
        )

    def test_secondary_collision_is_real_and_explicitly_rejected(self):
        sources = (
            "https://example.test/asset?i=184995",
            "https://example.test/asset?i=191756",
        )
        for source in sources:
            self.assertEqual(
                hashlib.sha256(source.encode("utf-8")).hexdigest()[:8],
                "df41192b",
            )
            self.assertIn(source, self.construction)
        for clause in (
            "MUST reject the assignment if the sole fallback also collides",
            "An already shortened candidate has no additional fallback",
            "MUST NOT append another suffix, overwrite a sibling, or choose a random discriminator",
            "test.example.asset.df41192b",
        ):
            self.assertIn(clause, self.construction)

    def test_forward_resolution_is_bounded_and_validates_metadata_before_acquisition(self):
        for clause in (
            "at most two distinct metadata locations",
            "MUST compare the returned `assetidentifier` exactly",
            "MUST NOT treat authorization, transport, malformed metadata, incomplete reads, or exhausted limits as absence",
            "No metadata or artifact acquisition is implicit in candidate computation",
        ):
            self.assertIn(clause, self.construction)
        resolution = self.text.split("### 5.4. Asset Resolution", 1)[1].split("### 5.5.", 1)[0]
        self.assertNotIn("by computation alone", resolution)
        self.assertIn("bounded forward procedure", resolution)

    def test_collision_examples_use_the_exact_source_hash(self):
        plain = self.construction.replace("`", "")
        for source, existing, candidate, expected in (
            ("a.b", "a.b -> a/b", "a.b", "a.b.2e7336dc"),
            ("a/b", "a.b -> a.b", "a.b", "a.b.c14cddc0"),
            ("pump", "Pump -> Pump", "pump", "pump.0b203c46"),
        ):
            suffix = hashlib.sha256(source.encode("utf-8")).hexdigest()[:8]
            self.assertEqual(expected, candidate + "." + suffix)
            self.assertIn(
                f"| {source} | {existing} | {candidate} | {expected} |",
                plain,
            )
        self.assertIn(
            "a.b.2e7336dc -> a.b.2e7336dc",
            plain,
        )


if __name__ == "__main__":
    print(f"Source: {SOURCE}", flush=True)
    print(f"SHA-256: {hashlib.sha256(SOURCE.read_bytes()).hexdigest()}", flush=True)
    unittest.main(verbosity=2)
