# coding: utf-8


from pandas import DataFrame
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

from dgp.lib.types import DataPacket
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory


class FileLoader(QObject):
    finished = pyqtSignal()
    loaded = pyqtSignal(DataPacket)
    # loaded = pyqtSignal(str, DataFrame)

    def __init__(self, path, dtype, flight, *args):
        super().__init__(*args)
        self.path = path
        self.data = None
        self._type = dtype.lower()
        self.flight = flight
        self.type_map = {'gravity': read_at1a, 'gps': import_trajectory}

    @pyqtSlot()
    def run(self):
        # TODO: Add exception handling
        df = self.type_map[self._type](self.path)
        self.data = DataPacket(df, self.path, self.flight, self._type)

        self.loaded.emit(self.data)
        self.finished.emit()


class ThreadedLoader:
    """Convenience class encapsulating the logic to create a QThread and FileLoader to load large data files."""
    def __init__(self):
        self.thread = None
        self.loader = None

    def load_file(self, path, dtype, flight, destination=None):
        """
        Load a data file using the specified 'loader' which is expected to accept a path parameter.
        For more complex loaders, a curried function should be passed which will then accept a single path param.
        :param path: File path of file to pass to loader function
        :param dtype:
        :param flight:
        :param destination: Callable function that the DataPacket should be passed to on completion of import
        :return: N/A
        """
        self.thread = QThread()
        self.loader = FileLoader(path, dtype, flight)
        self.loader.moveToThread(self.thread)
        self.thread.started.connect(self.loader.run)

        if destination is not None:
            self.loader.loaded.connect(destination)

        self.loader.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup)

        self.thread.start()
        return self.loader

    def add_hook(self, hook):
        if self.loader is not None:
            self.loader.finished.connect(hook)

    @property
    def data(self):
        return self.loader.data

    def cleanup(self):
        print("Thread finished")



