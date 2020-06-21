from abc import ABC, abstractmethod


class AbstractDataBase(ABC):
    """Connect and query database."""

    def __init__(self, db_name, host_name=None):
        """initialize database"""
        self.db_name = db_name
        self.host_name = host_name
        self._client = None
        self._db = None
        self.connect()

    @abstractmethod
    def connect(self):
        """connect to database"""
        pass

    @abstractmethod
    def close(self):
        """close database connection"""
        pass

    @abstractmethod
    def find(self, latest=True, **kwargs):
        """Find the records by kwargs."""
        pass
