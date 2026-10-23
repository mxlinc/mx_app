"""Regression tests for OHS hotspot storage formats and edit-save behaviour."""

import unittest
from pathlib import Path

from flask import Flask
from jsonschema import ValidationError, validate

from db import db
from models import QBank
from qb.handlers.ohs import OHSHandler
from schemas import OHS_SCHEMA


def ohs_json(hotspot, src='/qimage/7.png'):
    return {
        'id': 7,
        'type': 'ohs',
        'image': {'src': src, 'alt': '', 'hotspot': hotspot},
        'input': {},
        'answer': {'correct_hotspot_id': 'hs1'},
    }


LEGACY_HOTSPOT = {'id': 'hs1', 'x': 511, 'y': 50, 'width': 34, 'height': 54}
FRACTION_HOTSPOT = {'id': 'hs1', 'units': 'fraction', 'x': 0.25, 'y': 0.125, 'width': 0.1, 'height': 0.15}


class OHSSchemaTests(unittest.TestCase):
    def assertValid(self, hotspot):
        validate(instance=ohs_json(hotspot), schema=OHS_SCHEMA)

    def assertInvalid(self, hotspot):
        with self.assertRaises(ValidationError):
            validate(instance=ohs_json(hotspot), schema=OHS_SCHEMA)

    def test_legacy_pixel_hotspot_still_valid(self):
        self.assertValid(LEGACY_HOTSPOT)

    def test_legacy_hotspot_keeps_minimum_size(self):
        self.assertInvalid({**LEGACY_HOTSPOT, 'width': 0.5})

    def test_fraction_hotspot_valid(self):
        self.assertValid(FRACTION_HOTSPOT)

    def test_fraction_hotspot_must_be_within_image(self):
        self.assertInvalid({**FRACTION_HOTSPOT, 'x': 1.5})
        self.assertInvalid({**FRACTION_HOTSPOT, 'width': 0})
        self.assertInvalid({**FRACTION_HOTSPOT, 'height': 2})

    def test_unknown_units_rejected(self):
        self.assertInvalid({**FRACTION_HOTSPOT, 'units': 'percent'})


class OHSEditSaveTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_ENGINE_OPTIONS={
                'execution_options': {'schema_translate_map': {QBank.__table__.schema: None}},
            },
        )
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.metadata.create_all(db.engine, tables=[QBank.__table__])
        db.session.add(QBank(id=7, type='ohs', topic='t', subtopic='s', level='1',
                             json=ohs_json(dict(LEGACY_HOTSPOT))))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def save_edit(self, hotspot):
        return OHSHandler.save_question({
            'id': 7,
            'type': 'ohs',
            'topic': 't',
            'subtopic': 's',
            'level': '1',
            'image_data_url': None,
            'remove_image': False,
            'question': {
                'type': 'ohs',
                'input': {},
                'image': {'alt': '', 'hotspot': hotspot},
                'answer': {'correct_hotspot_id': 'hs1'},
            },
        })

    def test_redrawn_hotspot_is_saved_when_image_is_kept(self):
        q, error = self.save_edit(dict(FRACTION_HOTSPOT))

        self.assertIsNone(error)
        stored = db.session.get(QBank, 7).json['image']
        self.assertEqual(stored['src'], '/qimage/7.png')
        self.assertEqual(stored['hotspot'], FRACTION_HOTSPOT)

    def test_untouched_legacy_hotspot_is_stored_unchanged(self):
        q, error = self.save_edit(dict(LEGACY_HOTSPOT))

        self.assertIsNone(error)
        self.assertEqual(db.session.get(QBank, 7).json['image']['hotspot'], LEGACY_HOTSPOT)


if __name__ == '__main__':
    unittest.main()
