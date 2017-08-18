# coding: utf-8

import os
import configparser


class MeterConfig:
    """
    MeterConfig will contain the configuration of a specific gravity meter, giving the
    surveyer an easy way to specify the use of different meters on different flight lines.
    Initially dealing only with DGS AT1[A/M] meter types, need to add logic to handle other meters later.
    """
    def __init__(self, name, meter_type='AT1', **config):
        # TODO: Consider other meter types, what to do about different config values etc.

        self.name = name
        self.type = meter_type
        self.config = {k.lower(): v for k, v in config.items()}

    @staticmethod
    def from_ini(path):
        raise NotImplementedError

    def __getitem__(self, item):
        """Allow getting of configuration values using container type syntax e.g. value = MeterConfig['key']"""
        if isinstance(item, slice):
            raise NotImplementedError
        return self.config.get(item.lower(), None)

    def __setitem__(self, key, value):
        """Allow setting of configuration values using container type syntax e.g. MeterConfig['key'] = value"""
        try:
            value = float(value)
        except ValueError:
            pass
        self.config[key.lower()] = value

    def __len__(self):
        return len(self.config)


class AT1Meter(MeterConfig):
    """
    Subclass of MeterConfig for DGS AT1 Airborne/Marine meter configurations.
    Configuration values are cast to float upon
    """
    def __init__(self, name, **config):
        # Do some pre-processing of fields before passing to super
        at1config = self.process_config(self.get_valid_fields(), **config)
        super().__init__(name, 'AT1', **at1config)

    @staticmethod
    def get_valid_fields():
        # Sensor fields
        sensor_fields = ['g0', 'GravCal', 'LongCal', 'CrossCal', 'LongOffset', 'CrossOffset', 'stempgain',
                              'Temperature', 'stempoffset', 'pressgain', 'presszero', 'beamgain', 'beamzero',
                              'Etempgain', 'Etempzero']
        # Cross coupling Fields
        cc_fields = ['vcc', 've', 'al', 'ax', 'monitors']

        # Platform Fields
        platform_fields = ['Cross_Damping', 'Cross_Periode', 'Cross_Lead', 'Cross_Gain', 'Cross_Comp',
                                'Cross_Phcomp', 'Cross_sp', 'Long_Damping', 'Long_Periode', 'Long_Lead', 'Long_Gain',
                                'Long_Comp', 'Long_Phcomp', 'Long_sp', 'zerolong', 'zerocross', 'CrossSp', 'LongSp']

        # Create a set with all unique and valid field keys
        return set().union(sensor_fields, cc_fields, platform_fields)

    @staticmethod
    def process_config(valid_fields, **config):
        """Return a config dictionary by filtering out invalid fields, and lower-casing all keys"""
        def cast(value):
            try:
                return float(value)
            except ValueError:
                return value

        return {k.lower(): cast(v) for k, v in config.items() if k.lower() in map(str.lower, valid_fields)}

    @staticmethod
    def from_ini(path):
        """
        Read an AT1 Meter Configuration from a meter ini file
        :param path: path to meter ini file
        :return: instance of AT1Meter with configuration set by ini file
        """
        if not os.path.exists(path):
            raise OSError("Invalid path to ini.")
        config = configparser.ConfigParser(strict=False)
        config.read(path)

        sensor_fld = dict(config['Sensor'])
        xcoupling_fld = dict(config['crosscouplings'])
        platform_fld = dict(config['Platform'])

        name = str.strip(sensor_fld['meter'], '"')

        merge_config = {**sensor_fld, **xcoupling_fld, **platform_fld}
        at1config = AT1Meter.process_config(AT1Meter.get_valid_fields(), **merge_config)
        return AT1Meter(name, **at1config)
