# coding: utf-8

import pathlib
import tempfile
import unittest

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtTest as QtTest

import dgp.gui.dialogs as dlg
import core.types.enumerations as enums


class TestDialogs(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as td:
            self.m_prj = prj.AirborneProject(td, 'mock_project')
        self.m_flight = prj.Flight(self.m_prj, 'mock_flight')
        self.m_prj.add_flight(self.m_flight)
        self.m_data = [['h1', 'h2', 'h3'],
                       ['r1h1', 'r1h2', 'r1h3']]
        self.m_grav_path = pathlib.Path('tests/sample_gravity.csv')
        self.m_gps_path = pathlib.Path('tests/sample_trajectory.txt')

    def test_properties_dialog(self):
        t_dlg = dlg.PropertiesDialog(self.m_flight)
        self.assertEqual(8, t_dlg.form.rowCount())
        spy = QtTest.QSignalSpy(t_dlg.accepted)
        self.assertTrue(spy.isValid())
        QTest.mouseClick(t_dlg._btns.button(QtWidgets.QDialogButtonBox.Ok),
                         Qt.LeftButton)
        self.assertEqual(1, len(spy))

    # def test_advanced_import_dialog_gravity(self):
    #     t_dlg = dlg.AdvancedImportDialog(self.m_prj, self.m_flight,
    #                                      enums.DataTypes.GRAVITY)
    #     self.assertEqual(self.m_flight, t_dlg.flight)
    #     self.assertIsNone(t_dlg.path)
    #
    #     t_dlg.cb_format.setCurrentIndex(0)
    #     editor = t_dlg.editor
    #
    #     # Test format property setter, and reflection in editor format
    #     for fmt in enums.GravityTypes:
    #         self.assertNotEqual(-1, t_dlg.cb_format.findData(fmt))
    #         t_dlg.format = fmt
    #         self.assertEqual(t_dlg.format, editor.format)
    #
    #     t_dlg.path = self.m_grav_path
    #     self.assertEqual(self.m_grav_path, t_dlg.path)
    #     self.assertEqual(list(t_dlg.cb_format.currentData().value),
    #                      editor.columns)
    #
    #     # Set formatter back to type AT1A for param testing
    #     t_dlg.format = enums.GravityTypes.AT1A
    #     self.assertEqual(t_dlg.format, enums.GravityTypes.AT1A)
    #
    #     # Test behavior of skiprow property
    #     # Should return None if unchecked, and 1 if checked
    #     self.assertIsNone(editor.skiprow)
    #     editor.skiprow = True
    #     self.assertEqual(1, editor.skiprow)
    #
    #     # Test generation of params property on dialog accept()
    #     t_dlg.accept()
    #     result_params = dict(path=self.m_grav_path,
    #                          columns=list(enums.GravityTypes.AT1A.value),
    #                          skiprows=1,
    #                          subtype=enums.GravityTypes.AT1A)
    #     self.assertEqual(result_params, t_dlg.params)
    #     self.assertEqual(self.m_flight, t_dlg.flight)

    # def test_advanced_import_dialog_trajectory(self):
    #     t_dlg = dlg.AdvancedImportDialog(self.m_prj, self.m_flight,
    #                                      enums.DataTypes.TRAJECTORY)
    #
    #     # Test all GPSFields represented, and setting via format property
    #     for fmt in enums.GPSFields:
    #         self.assertNotEqual(-1, t_dlg.cb_format.findData(fmt))
    #         t_dlg.format = fmt
    #         self.assertEqual(fmt, t_dlg.format)
    #         col_fmt = t_dlg.params['subtype']
    #         self.assertEqual(fmt, col_fmt)
    #     t_dlg.format = enums.GPSFields.hms
    #
    #     # Verify expected output, ordered correctly
    #     hms_expected = ['mdy', 'hms', 'lat', 'long', 'ell_ht']
    #     self.assertEqual(hms_expected, t_dlg.params['columns'])
