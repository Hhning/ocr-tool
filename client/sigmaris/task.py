'''async task
Make task don't block main thread
'''
import os
import atexit
import logging
from functools import partial
from concurrent.futures import thread, ThreadPoolExecutor

from PyQt5.QtCore import QObject, pyqtSignal

from sigmaris.query import pipeline, getStatus, raisePriority
from sigmaris.utils import singleton

_logger = logging.getLogger(__name__)


class StatusAction(object):

    def __init__(self, edit=False, open=False):
        self.edit = edit
        self.open = open


@singleton
class Task(QObject):

    statusGetted = pyqtSignal(tuple)    # (QueryResult, invoke)
    pipelined = pyqtSignal(tuple)       # (PatientId, QueryResult)
    priorityRaised = pyqtSignal(dict) # (Job_id, priority)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ''
        self.ocrPool = ThreadPoolExecutor(4)
        self.ocrFutures = []
        self.statusPool = ThreadPoolExecutor(3)
        self.statusFutures = []
        self.raisePool = ThreadPoolExecutor(1)
        self.raiseFutures = []
        atexit.register(self.onExit)

    def submitPipeline(self, files, data, isManual=False):
        future = self.ocrPool.submit(pipeline, files, data)
        future.add_done_callback(partial(self.pipelineCallback, isManual=isManual))
        self.ocrFutures.append(future)

    def submitStatus(self, text, action=None):
        self.text = text
        future = self.statusPool.submit(getStatus, text)
        future.add_done_callback(partial(self.statusCallback, name=text, action=action))
        self.statusFutures.append(future)

    def submitRaise(self, job_id):
        future = self.raisePool.submit(raisePriority, job_id)
        future.add_done_callback(partial(self.raiseCallback, job_id=job_id))
        self.raiseFutures.append(future)

    def pipelineCallback(self, future, isManual):
        # TODO isManual可以用于手动截图失败后的提示标志
        if future not in self.ocrFutures:
            return
        index = self.ocrFutures.index(future)
        self.ocrFutures.remove(future)
        if future.cancelled() or future.exception():
            _logger.debug('Future cacelled or exception')
        else:
            result = future.result()
            if result:          # 接收到后面结果时才清空前面的future
                for i in range(index):
                    self.ocrFutures[i].cancel()
                self.ocrFutures = self.ocrFutures[index:]
                self.pipelined.emit(result)

    def statusCallback(self, future, name, action):
        if future not in self.statusFutures:
            return
        index = self.statusFutures.index(future)
        for i in range(index):
            self.statusFutures[i].cancel()
        self.statusFutures = self.statusFutures[index+1:]

        if future.cancelled() or name != self.text:
            return
        status = future.result()
        self.statusGetted.emit((status, action))

    def raiseCallback(self, future, job_id):
        if future not in self.raiseFutures:
            return
        index = self.raiseFutures.index(future)
        for i in range(index):
            self.raiseFutures[i].cancel()
        self.raiseFutures = self.raiseFutures[index+1:]

        if future.cancelled() or future.exception():
            return
        result = future.result()
        self.priorityRaised.emit(result)

    def cancelTasks(self):
        pass

    def clearTasks(self):
        self.ocrPool._threads.clear()
        self.statusPool._threads.clear()
        self.raisePool._threads.clear()
        thread._threads_queues.clear()
        self.ocrFutures = []
        self.statusFutures = []
        self.raiseFutures = []

    def onExit(self):
        self.clearTasks()


task = Task()
