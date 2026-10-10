"""Offline tests; tiny PNG fixtures are never presented as generated artwork."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

import lesson_images as helper


def fixture_png(path, width=32, height=18):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' +
                     chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress((b'\0' + b'\xff' * width * 3) * height)) +
                     chunk(b'IEND', b''))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = {'lesson_title': 'Test lesson', 'audience': 'Beginners',
                     'style': 'Navy outlines and white background.', 'allow_humans': False,
                     'sections': [dict(section_number=n, section_title='Same title',
                                       transcript=f'Exact narration {n}.\nSecond line.',
                                       learning_goal='Understand a relationship',
                                       visual_concept='Two objects connected by a directional arrow',
                                       composition='Wide diagram', accuracy_notes='Arrow from cause to effect',
                                       labels=[]) for n in [8, 3, 12, 1, 2, 9]]}
        self.input = self.root / 'plan.json'
        self.input.write_text(json.dumps(self.plan), encoding='utf-8')
        self.manifest = helper.prepare(self.input, self.root / 'output')

    def test_six_sections_order_transcripts_and_names(self):
        data = helper.load_manifest(self.manifest)
        self.assertEqual([r['section_number'] for r in data['sections']], [8, 3, 12, 1, 2, 9])
        self.assertEqual([r['transcript'] for r in data['sections']],
                         [r['transcript'] for r in self.plan['sections']])
        self.assertEqual(len({r['image_filename'] for r in data['sections']}), 6)
        self.assertEqual(data['sections'][0]['image_filename'], '01-same-title.png')
        self.assertEqual(len(helper.verify(self.manifest)), 6)
        for row in data['sections']:
            self.assertIn(self.plan['style'], row['generated_image_prompt'])
            self.assertNotIn(row['transcript'], row['generated_image_prompt'])

    def test_full_save_verify_hash_and_no_overwrite(self):
        image = self.root / 'fixture.png'
        fixture_png(image)
        for order in range(1, 7):
            helper.attach(self.manifest, order, image, True)
        self.assertEqual(helper.verify(self.manifest), [])
        with self.assertRaises(ValueError):
            helper.attach(self.manifest, 1, image, True)
        target = self.manifest.parent / '01-same-title.png'
        target.write_bytes(target.read_bytes() + b'changed')
        self.assertTrue(any('differs' in item for item in helper.verify(self.manifest)))

    def test_wrong_ratio_format_and_review(self):
        image = self.root / 'bad.png'
        fixture_png(image, 30, 20)
        with self.assertRaises(ValueError):
            helper.attach(self.manifest, 1, image, True)
        image.write_text('Not PNG', encoding='utf-8')
        with self.assertRaises(ValueError):
            helper.attach(self.manifest, 1, image, True)
        fixture_png(image)
        with self.assertRaises(ValueError):
            helper.attach(self.manifest, 1, image, False)

    def test_whole_pixel_rounding_preserves_native_image(self):
        image = self.root / 'rounded.png'
        fixture_png(image, 1672, 941)
        original = image.read_bytes()
        target = helper.attach(self.manifest, 1, image, True)
        self.assertEqual(Path(target).read_bytes(), original)
        self.assertEqual(helper.png_size(target), (1672, 941))
        fixture_png(image, 1672, 943)
        with self.assertRaises(ValueError):
            helper.png_size(image)

    def test_block_resume_actual_prompt(self):
        helper.block(self.manifest, 2, 'Export failed')
        image = self.root / 'fixture.png'
        fixture_png(image)
        prompt = self.root / 'revised.txt'
        prompt.write_text('Actual revised generation prompt', encoding='utf-8')
        helper.attach(self.manifest, 2, image, True, prompt)
        row = helper.load_manifest(self.manifest)['sections'][1]
        self.assertEqual(row['status'], 'complete')
        self.assertNotIn('error', row)
        self.assertEqual(row['generated_image_prompt'], prompt.read_text())
        self.assertNotEqual(row['initial_prompt'], row['generated_image_prompt'])

    def test_safe_paths_unicode_and_versioned_output(self):
        self.assertNotIn('/', helper.slug('../../Title: name'))
        self.assertNotIn('\\', helper.slug('a\\b'))
        self.assertEqual(helper.slug('الماء'), 'الماء')
        sibling = helper.prepare(self.input, self.root / 'output')
        self.assertNotEqual(sibling.parent, self.manifest.parent)
        data = helper.read_json(self.manifest)
        data['sections'][0]['image_filename'] = '../escape.png'
        self.manifest.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            helper.load_manifest(self.manifest)

    def test_invalid_input_before_output(self):
        broken = copy.deepcopy(self.plan)
        broken['sections'][-1]['transcript'] = ''
        self.input.write_text(json.dumps(broken), encoding='utf-8')
        destination = self.root / 'invalid-output'
        with self.assertRaises(ValueError):
            helper.prepare(self.input, destination)
        self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
