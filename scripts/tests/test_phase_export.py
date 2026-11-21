"""Admission is a data boundary, not a cosmetic source label."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('phase_export',Path(__file__).resolve().parents[1]/'research/export-phase-demo.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PhaseExportTests(unittest.TestCase):
    def test_failed_methods_cannot_create_a_success_catalogue(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'report.json').write_text(json.dumps({'admitted':{'memoryless':False,'phase_memory':False}}))
            with self.assertRaisesRegex(ValueError,'no method passed'):module.export(root,root/'out')
            self.assertFalse((root/'out').exists())

    def test_self_declared_admission_cannot_override_per_seed_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            good={'full_success':True,'delivered_kg':2000,'initial_payload_kg':0,'reason':'success'}
            bad={'full_success':False,'delivered_kg':0,'initial_payload_kg':0,'reason':'time_limit'}
            report={'admitted':{'memoryless':False,'phase_memory':True},'selection':{},'plan':{'source':{'fixture':True}},'tests':{'phase_memory-7':[good]*27+[bad]*5}}
            (root/'report.json').write_text(json.dumps(report));(root/'selection.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'per-seed'):module.export(root,root/'out')
            self.assertFalse((root/'out/catalogue.json').exists())
