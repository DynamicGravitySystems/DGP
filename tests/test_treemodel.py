# coding: utf-8

from .context import dgp

import unittest

from dgp.lib import types, project
from dgp.gui import models


class TestModels(unittest.TestCase):
    def setUp(self):
        self.uid = "uid123"
        self.ti = types.TreeItem(self.uid)
        self.uid_ch0 = "uidchild0"
        self.uid_ch1 = "uidchild1"
        self.child0 = types.TreeItem(self.uid_ch0)
        self.child1 = types.TreeItem(self.uid_ch1)

    def test_treeitem(self):
        """Test new tree item base class"""
        self.assertIsInstance(self.ti, types.AbstractTreeItem)
        self.assertEqual(self.ti.uid, self.uid)
        with self.assertRaises(NotImplementedError):
            res = self.ti.data()

        self.assertEqual(self.ti.child_count(), 0)
        self.assertEqual(self.ti.row(), 0)

    def test_tree_child(self):
        uid = "uid123"
        child_uid = "uid345"
        ti = types.TreeItem(uid)
        child = types.TreeItem(child_uid)
        ti.append_child(child)
        ti.append_child(child)
        # Appending the same item twice should have no effect
        self.assertEqual(ti.child_count(), 1)

        self.assertEqual(ti.child(child_uid), child)
        self.assertEqual(child.parent, ti)

        with self.assertRaises(AssertionError):
            ti.append_child("Bad Child")

        self.assertEqual(ti.indexof(child), 0)
        child1 = types.TreeItem("uid456", parent=ti)
        self.assertEqual(child1.parent, ti)
        self.assertEqual(child1, ti.child("uid456"))
        self.assertEqual(child1.row(), 1)

    def test_tree_iter(self):
        """Test iteration of objects in TreeItem"""
        self.ti.append_child(self.child0)
        self.ti.append_child(self.child1)

        child_list = [self.child0, self.child1]
        self.assertEqual(self.ti.child_count(), 2)
        for child in self.ti:
            self.assertIn(child, child_list)
            self.assertIsInstance(child, types.AbstractTreeItem)

    def test_tree_len(self):
        """Test __len__ method of TreeItem"""
        self.assertEqual(len(self.ti), 0)
        self.ti.append_child(self.child0)
        self.ti.append_child(self.child1)
        self.assertEqual(len(self.ti), 2)










