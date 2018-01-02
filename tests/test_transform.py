# coding: utf-8

import unittest
import numpy as np
import pandas as pd
import csv
from copy import deepcopy

# from .context import  dgp
from tests import sample_dir
from dgp.lib.transform import (TransformChain, DataWrapper, Transform,
                               createtransform, transform_registry,
                               RegisterTransformClass)
from dgp.lib.derivatives import Eotvos, CentralDiff2
from dgp.lib.filters import FIRlowpassfilter
import dgp.lib.trajectory_ingestor as ti


class TestTransform(unittest.TestCase):

    def test_createtransform_decorator(self):

        @createtransform
        def transform1(df, *, a=2, b=3):
            df['A'] = df['A'] + a * b
            return df

        df = pd.DataFrame({'A': range(11), 'B': range(11)})

        tc = TransformChain()
        tf_inst = transform_registry['transform1']()

        # check transform class instance attributes
        self.assertTrue(tf_inst.a == 2)
        self.assertTrue(tf_inst.b == 3)

        tc.addtransform(tf_inst)

        self.assertTrue(len(tc) == 1)

        new_df_A = tc.apply(df)

        df_A1 = deepcopy(df)
        df_A1['A'] = df_A1['A'] + 2 * 3

        self.assertTrue(new_df_A.equals(df_A1))

        # test change of instance attributes
        df_A2 = deepcopy(df)
        df_A2['A'] = df_A2['A'] + 4 * 2

        tf_inst.a = 4
        tf_inst.b = 2
        self.assertTrue(tf_inst.a == 4)
        self.assertTrue(tf_inst.b == 2)

        new_df_A = tc.apply(df)

        self.assertTrue(new_df_A.equals(df_A2))

    def test_transform_subclass(self):
        @RegisterTransformClass('transform2')
        class Transform2(Transform):
            var_list = [('a', 2), ('b', 3)]

            def func(self, df, *, a, b):
                df['A'] = df['A'] + a * b
                return df

        df = pd.DataFrame({'A': range(11), 'B': range(11)})

        tf_inst = Transform2()

        # check transform class instance attributes
        self.assertTrue(tf_inst.a == 2)
        self.assertTrue(tf_inst.b == 3)

        df_cp = deepcopy(df)
        new_df_A = tf_inst(df_cp)
        df_A1 = deepcopy(df)
        df_A1['A'] = df_A1['A'] + 2 * 3

        self.assertTrue(new_df_A.equals(df_A1))

        # override default keyword values
        tf_inst = Transform2(a=4, b=2)

        self.assertTrue(tf_inst.a == 4)
        self.assertTrue(tf_inst.b == 2)

        df_cp = deepcopy(df)
        new_df_A = tf_inst(df_cp)
        df_A2 = deepcopy(df)
        df_A2['A'] = df_A2['A'] + 4 * 2

        self.assertTrue(new_df_A.equals(df_A2))

    def test_basic_transform_chain_ops(self):

        def transform1(df):
            df['A'] = df['A'] + 3.
            return df

        def transform2(df):
            df['A'] = df['A'] + df['B']
            return df

        def transform3(df):
            df = (df + df.shift(1)).dropna()
            return df

        df = pd.DataFrame({'A': range(11), 'B': range(11)})
        tc = TransformChain()
        tc.addtransform(transform1)
        tc.addtransform(transform2)
        tc.addtransform(transform3)

        self.assertTrue(len(tc) == 3)

        new_df_A = tc.apply(df)

        df_A = deepcopy(df)
        df_A['A'] = df_A['A'] + 3.
        df_A['A'] = df_A['A'] + df_A['B']
        df_A = (df_A + df_A.shift(1)).dropna()

        self.assertTrue(new_df_A.equals(df_A))

        # test reordering
        reordering = {tc[2]: 0, tc[0]: 2}
        reordered_uids = [tc.ordering[-1], tc.ordering[1], tc.ordering[0]]
        tc.reorder(reordering)

        self.assertTrue(tc.ordering == reordered_uids)

        xforms = [transform3, transform2, transform1]
        reordered_xforms = [t for t in tc]
        self.assertTrue(xforms == reordered_xforms)

    def test_basic_data_wrapper(self):

        def transform1a(df):
            df['A'] = df['A'] + 3.
            return df

        def transform2a(df):
            df['A'] = df['A'] + df['B']
            return df

        def transform1b(df):
            df['A'] = df['A'] * 3
            return df

        def transform2b(df):
            df['C'] = df['A'] + df['B'] * 2
            return df

        tc_a = TransformChain()
        tc_a.addtransform(transform1a)
        tc_a.addtransform(transform2a)

        tc_b = TransformChain()
        tc_b.addtransform(transform1b)
        tc_b.addtransform(transform2b)

        df = pd.DataFrame({'A': range(11), 'B': range(11)})
        wrapper = DataWrapper(df)
        df_a = wrapper.applychain(tc_a)
        df_b = wrapper.applychain(tc_b)

        df_a_true = deepcopy(df)
        df_a_true['A'] = df_a_true['A'] + 3.
        df_a_true['A'] = df_a_true['A'] + df_a_true['B']

        df_b_true = deepcopy(df)
        df_b_true['A'] = df_b_true['A'] * 3
        df_b_true['C'] = df_b_true['A'] + df_b_true['B'] * 2

        self.assertTrue(df_a.equals(df_a_true))
        self.assertTrue(df_b.equals(df_b_true))

        self.assertTrue(len(wrapper) == 2)

        self.assertTrue(df_a.equals(wrapper.modified[tc_a.uid]))
        self.assertTrue(df_b.equals(wrapper.modified[tc_b.uid]))

    def test_simple_filter_class(self):

        def lp_filter(data, fc, fs, window):
            return data

        lp = FIRlowpassfilter(func=lp_filter, fc=10, fs=100)
        self.assertTrue(lp.fc == 10)
        self.assertTrue(lp.fs == 100)

        data = np.ones(5)
        res = lp(data)
        np.testing.assert_array_equal(res, data)

    def _find_comp(self, sig, fs):
        w = np.fft.fft(sig)
        freqs = np.fft.fftfreq(len(w))
        n = np.argpartition(np.abs(w), -10)[-10:]
        ind = n[np.abs(w)[n] > 100]
        freq = np.unique(np.abs(freqs[ind])) * fs
        return list(freq)

    def test_lp_filter_class(self):

        # def lp_filter(data, fc, fs, window):
        #     filter_len = 1 / fc
        #     nyq = fs / 2.0
        #     wn = fc / nyq
        #     N = int(2.0 * filter_len * fs)
        #     taps = signal.firwin(N, wn, window=window, nyq=nyq)
        #     filtered_data = signal.filtfilt(taps, 1.0, data, padtype='even', padlen=80)
        #     return filtered_data

        # generate a signal
        fs = 100 # Hz
        frequencies = [1.2, 3, 5, 7] # Hz
        start = 0
        stop = 10 # s
        t = np.linspace(start, stop, fs * (stop - start))
        sig = np.zeros(len(t))
        for f in frequencies:
            sig += np.sin(2 * np.pi * f * t )

        freq_before = self._find_comp(sig, fs)

        lp = FIRlowpassfilter(fc=5, fs=fs)

        self.assertTrue(lp.window == 'blackman')

        filtered_sig = lp(sig)
        freq_after = self._find_comp(filtered_sig, fs)
        self.assertTrue(freq_after == [1.2, 3])

    @unittest.skip("tempo")
    def test_transform_eotvos(self):
        """Test Eotvos function against corrections generated with MATLAB program."""
        # Ensure gps_fields are ordered correctly relative to test file
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_stats', 'pdop']
        data = ti.import_trajectory('tests/sample_data/eotvos_short_input.txt', columns=gps_fields, skiprows=1,
                                    timeformat='hms')

        result_eotvos = []
        with sample_dir.joinpath('eotvos_short_result.csv').open() as fd:
            test_data = csv.DictReader(fd)
            for line in test_data:
                result_eotvos.append(float(line['Eotvos_full']))
        lat = data['lat'].values
        lon = data['long'].values
        ht = data['ell_ht'].values
        rate = 10

        derivative_func = CentralDiff2()
        eotvos_func = Eotvos(derivative=derivative_func)
        eotvos_a = eotvos_func(lat=lat, lon=lon, ht=ht)

        for i, value in enumerate(eotvos_a):
            try:
                self.assertAlmostEqual(value, result_eotvos[i], places=2)
            except AssertionError:
                print("Invalid assertion at data line: {}".format(i))
                raise AssertionError

    @unittest.skip("test_transform_eotvos_npgradient not yet working.")
    def test_transform_eotvos_npgradient(self):
        """Test Eotvos function against corrections generated with MATLAB program."""
        # Ensure gps_fields are ordered correctly relative to test file
        gps_fields = ['mdy', 'hms', 'lat', 'long', 'ortho_ht', 'ell_ht', 'num_stats', 'pdop']
        data = ti.import_trajectory('tests/sample_data/eotvos_short_input.txt', columns=gps_fields, skiprows=1,
                                    timeformat='hms')

        result_eotvos = []
        with sample_dir.joinpath('eotvos_short_result.csv').open() as fd:
            test_data = csv.DictReader(fd)
            for line in test_data:
                result_eotvos.append(float(line['Eotvos_full']))
        lat = data['lat'].values
        lon = data['long'].values
        ht = data['ell_ht'].values
        rate = 10

        def npgradient(data, n=1):
            if n == 1:
                return np.gradient(data, edge_order=1)
            elif n == 2:
                return np.gradient(np.gradient(data, edge_order=1), edge_order=1)
            else:
                raise ValueError('Invalid value for parameter n {1 or 2}')

        eotvos_func = Eotvos(derivative=Derivative(npgradient))
        eotvos_a = eotvos_func(lat=lat, lon=lon, ht=ht)

        # print(eotvos_a)
        # print(result_eotvos)

        for i, value in enumerate(eotvos_a):
            try:
                self.assertAlmostEqual(value, result_eotvos[i], places=2)
            except AssertionError:
                print("Invalid assertion at data line: {}".format(i))
                raise AssertionError