# coding=utf-8

"""
transform.py
Library for data transformation wrapper classes

"""

from copy import deepcopy

class DataWrapper:
    def __init__(self, frame: DataFrame):
        self.df = frame
        self.transforms = {}
        self.ordering = []

    def add_transform(self, transform: Callable):
        self.transforms[uid] = transform
        self.ordering.append(uid)
        return uid

    def remove_transform(self, uid):
        del self.transforms[uid]
        self.ordering.remove(uid)

    def reorder(self, reordering):
        order = sorted(reordering.values(), key=reordering.__get_item__)
        for uid in order:
            self.ordering.remove(uid)
            self.ordering.insert(reordering[uid], uid)
        return self.ordering

    def apply_transforms(self):
        df = deepcopy(self.df)
        for uid in self.ordering:
            df = self.transforms[uid](df)
        return df

    def __len__(self):
        return len(self.transforms.items())
