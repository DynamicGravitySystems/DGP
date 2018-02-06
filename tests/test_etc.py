from .context import dgp
import unittest
import numpy as np
import pandas as pd

from dgp.lib.etc import align_frames


class TestAlignOps(unittest.TestCase):
    # TODO: Test with another DatetimeIndex
    # TODO: Test with other interpolation methods
    # TODO: Tests for interp_only

    def test_align_args(self):
        frame1 = pd.Series(np.arange(10))
        index1 = pd.Timestamp('2018-01-29 15:19:28.000') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame1.index = index1

        frame2 = pd.Series(np.arange(10, 20))
        index2 = pd.Timestamp('2018-01-29 15:00:28.002') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame2.index = index2

        msg = 'Invalid value for align_to parameter: invalid'
        with self.assertRaises(ValueError, msg=msg):
            align_frames(frame1, frame2, align_to='invalid')

        msg = 'Frames do not overlap'
        with self.assertRaises(ValueError, msg=msg):
            align_frames(frame1, frame2)

        frame1 = pd.Series(np.arange(10))
        index1 = pd.Timestamp('2018-01-29 15:00:28.000') + \
                 pd.to_timedelta(np.arange(10), unit='s')
        frame1.index = index1

        frame2 = pd.Series(np.arange(10, 20))
        index2 = pd.Timestamp('2018-01-29 15:19:28.002') + \
                 pd.to_timedelta(np.arange(10), unit='s')
        frame2.index = index2

        msg = 'Frames do not overlap'
        with self.assertRaises(ValueError, msg=msg):
            align_frames(frame1, frame2)

    def test_align_crop(self):
        frame1 = pd.Series(np.arange(10))
        index1 = pd.Timestamp('2018-01-29 15:19:30.000') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame1.index = index1

        frame2 = pd.Series(np.arange(10, 20))
        index2 = pd.Timestamp('2018-01-29 15:19:28.002') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame2.index = index2

        # align left
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='left')
        self.assertTrue(aframe1.index.equals(aframe2.index))

        # align right
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='right')
        self.assertTrue(aframe1.index.equals(aframe2.index))

    def test_align_and_crop_series(self):
        frame1 = pd.Series(np.arange(10))
        index1 = pd.Timestamp('2018-01-29 15:19:28.000') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame1.index = index1

        frame2 = pd.Series(np.arange(10, 20))
        index2 = pd.Timestamp('2018-01-29 15:19:28.002') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame2.index = index2

        # align left
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='left')
        self.assertTrue(aframe1.index.equals(aframe2.index))

        # align right
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='right')
        self.assertTrue(aframe1.index.equals(aframe2.index))

    def test_align_and_crop_df(self):
        frame1 = pd.DataFrame(np.array([np.arange(10), np.arange(10, 20)]).T)
        index1 = pd.Timestamp('2018-01-29 15:19:28.000') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame1.index = index1

        frame2 = pd.DataFrame(np.array([np.arange(20,30), np.arange(30, 40)]).T)
        index2 = pd.Timestamp('2018-01-29 15:19:28.002') + \
            pd.to_timedelta(np.arange(10), unit='s')
        frame2.index = index2

        # align left
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='left')
        self.assertFalse(aframe1.index.empty)
        self.assertFalse(aframe2.index.empty)
        self.assertTrue(aframe1.index.equals(aframe2.index))

        # align right
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='right')
        self.assertFalse(aframe1.index.empty)
        self.assertFalse(aframe2.index.empty)
        self.assertTrue(aframe1.index.equals(aframe2.index))

    def test_align_and_crop_df_fill(self):
        frame1 = pd.DataFrame(np.array([np.arange(10), np.arange(10, 20)]).T)
        frame1.columns = ['A', 'B']
        index1 = pd.Timestamp('2018-01-29 15:19:28.000') + \
                 pd.to_timedelta(np.arange(10), unit='s')
        frame1.index = index1

        frame2 = pd.DataFrame(np.array([np.arange(20, 30), np.arange(30, 40)]).T)
        frame2.columns = ['C', 'D']
        index2 = pd.Timestamp('2018-01-29 15:19:28.002') + \
                 pd.to_timedelta(np.arange(10), unit='s')
        frame2.index = index2

        aframe1, aframe2 = align_frames(frame1, frame2, fill={'B': 'bfill'})
        self.assertTrue(aframe1['B'].equals(frame1['B'].iloc[1:].astype(float)))

        left, right = frame1.align(frame2, axis=0, copy=True)
        left = left.fillna(method='bfill')
        left = left.reindex(frame2.index).dropna()
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='right',
                                        fill={'B': 'bfill'})
        self.assertTrue(aframe1['B'].equals(left['B']))

        left, right = frame1.align(frame2, axis=0, copy=True)
        left = left.fillna(value=0)
        left = left.reindex(frame2.index).dropna()
        aframe1, aframe2 = align_frames(frame1, frame2, align_to='right',
                                        fill={'B': 0})
        self.assertTrue(aframe1['B'].equals(left['B']))
