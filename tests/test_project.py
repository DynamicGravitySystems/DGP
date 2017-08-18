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



