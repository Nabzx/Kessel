import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location("reference", Path(__file__).parents[1] / "prepare-tunnel-reference.py")
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def sample():
    rows = []
    for x in range(-10, 11):
        rows.append(struct.pack("<12fH", 0, 0, 1, x, -1, 0, x+0.5, 1, 0, x, 0, 2, 0))
    return bytes(80) + struct.pack("<I", len(rows)) + b"".join(rows)


class TunnelReferenceChecks(unittest.TestCase):
    def test_crop_is_deterministic_credited_and_not_a_physical_survey(self):
        a, meta = reference.crop_reference(sample(), span=6)
        self.assertEqual((a, meta), reference.crop_reference(sample(), span=6))
        self.assertLess(meta["triangles"], meta["source_triangles"])
        self.assertEqual(len(a), meta["triangles"] * 9 * 4)
        self.assertIsNone(meta["physical_units"])
        self.assertIsNone(meta["crs"])
        self.assertTrue(meta["reference_only"])
        self.assertIn("CC BY 4.0", meta["attribution"])

    def test_truncated_and_nonfinite_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            reference.crop_reference(sample()[:-1])
        raw = bytearray(sample())
        struct.pack_into("<f", raw, 96, float("nan"))
        with self.assertRaises(ValueError):
            reference.crop_reference(raw)

    def test_invalid_crop_span_is_rejected(self):
        for span in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                reference.crop_reference(sample(), span)


if __name__ == "__main__":
    unittest.main()
