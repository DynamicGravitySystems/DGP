# coding: utf-8

import unittest
import configparser

from .context import dgp
from dgp.meterconfig import *

os.chdir('tests')


class TestMeterconfig(unittest.TestCase):
    def setUp(self):
        self.ini_path = os.path.abspath('./at1m.ini')
        self.config = {
            'g0': 10000.0,
            'GravCal': 227626.0,
            'LongCal': 200.0,
            'CrossCal': 200.1,
            'vcc': 0.0,
            've': 0.0,
            'Cross_Damping': 550.0,
            'Long_Damping': 550.0,
            'at1_invalid': 12345.8
        }

    def test_MeterConfig(self):
        mc = MeterConfig(name='Test-1', **self.config)
        self.assertEqual(mc.name, 'Test-1')

        # Test get, set and len methods of the MeterConfig class
        self.assertEqual(len(mc), len(self.config))

        for k in self.config.keys():
            self.assertEqual(mc[k], self.config[k])
            # Test case-insensitive handling
            self.assertEqual(mc[k.lower()], self.config[k])

        mc['g0'] = 500.01
        self.assertEqual(mc['g0'], 500.01)
        self.assertIsInstance(mc['g0'], float)
        # Test the setting of non-float types
        mc['monitor'] = True
        self.assertTrue(mc['monitor'])

        mc['str_val'] = 'a string'
        self.assertEqual(mc['str_val'], 'a string')

        # Test the class handling of invalid requests/types
        with self.assertRaises(NotImplementedError):
            mc[0: 3]

        with self.assertRaises(NotImplementedError):
            MeterConfig.from_ini(self.ini_path)

    def test_AT1Meter_config(self):
        at1 = AT1Meter('AT1M-5', **self.config)

        self.assertEqual(at1.name, 'AT1M-5')

        # Test that invalid field was not set
        self.assertIsNone(at1['at1_invalid'])
        valid_fields = {k: v for k, v in self.config.items() if k != 'at1_invalid'}
        for k in valid_fields.keys():
            # Check all valid fields were set
            self.assertEqual(at1[k], valid_fields[k])

    def test_AT1Meter_from_ini(self):
        at1 = AT1Meter.from_ini(self.ini_path)

        # Check type inheritance
        self.assertIsInstance(at1, AT1Meter)
        self.assertIsInstance(at1, MeterConfig)

        self.assertEqual(at1.name, 'AT1M-1U')

        cfp = configparser.ConfigParser(strict=False)  # strict=False to allow for duplicate keys in config
        cfp.read(self.ini_path)

        skip_fields = ['meter', '00gravcal']
        for k, v in cfp['Sensor'].items():
            if k in skip_fields:
                continue
            self.assertEqual(float(cfp['Sensor'][k]), at1[k])

