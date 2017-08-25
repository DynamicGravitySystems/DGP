# coding: utf-8

import unittest
import random

from .context import dgp
from dgp.project import *
from dgp.meterconfig import *


class TestProject(unittest.TestCase):

    def setUp(self):
        """Set up some dummy classes for testing use"""
        self.project = AirborneProject(path='.', name='Test Airborne Project')

        # Sample values for testing meter configs
        self.meter_vals = {
            'gravcal': random.randint(200000, 300000),
            'longcal': random.uniform(150.0, 250.0),
            'crosscal': random.uniform(150.0, 250.0),
            'cross_lead': random.random()
        }
        self.at1a5 = MeterConfig(name="AT1A-5", **self.meter_vals)
        self.project.add_meter(self.at1a5)

    def test_load_project(self):
        project = AirborneProject.load_yaml('tests/test_project.yaml')
        self.assertEqual(project.name, 'Test Project')
        self.assertEqual(project.projectdir, os.path.abspath('.'))

        self.assertEqual(len(project.flights), 1)
        f0uid = '4fec08e6-6fe3-422e-a46a-80af263e7364'

        self.assertIsInstance(project.flights[f0uid].meter, AT1Meter)
        self.assertEqual(project.flights[f0uid].meter['LongCal'], 200)

    def test_pickle_project(self):
        # TODO: Add further complexity to testing of project
        flight = Flight(self.at1a5)
        flight.add_line(100, 250.5)
        self.project.add_flight(flight)

        save_loc = 'tests/test_project.p'

        self.project.save(save_loc)

        loaded_project = AirborneProject.load(save_loc)
        self.assertIsInstance(loaded_project, AirborneProject)
        self.assertEqual(len(loaded_project.flights), 1)
        self.assertEqual(loaded_project.flights[flight.uid].uid, flight.uid)
        self.assertEqual(loaded_project.flights[flight.uid].meter.name, 'AT1A-5')

        # Cleanup
        try:
            os.remove(save_loc)
        except OSError:
            pass

    def test_flight_iteration(self):
        test_flight = Flight(self.at1a5)
        line0 = test_flight.add_line(100.1, 200.2)
        line1 = test_flight.add_line(210, 350.3)
        lines = [line0, line1]

        for line in test_flight:
            print(line)
            self.assertTrue(line in lines)

    def test_associate_flight_data(self):
        """Test adding a data file and associating it with a specific flight"""
        flt = Flight(self.at1a5)
        self.project.add_flight(flt)

        data1 = 'tests/test_data.csv'
        self.project.add_data(data1, flight=flt)

        data1path = os.path.abspath(data1)
        self.assertTrue(data1path in self.project.data_sources.values())


class TestMeterconfig(unittest.TestCase):
    def setUp(self):
        self.ini_path = os.path.abspath('tests/at1m.ini')
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



