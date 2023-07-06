import fnmatch
import logging.config
import os
import time
import json
from unittest import TestCase

from .mockLogzioListener import listener


def _find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))

        break  # Not descending recursively
    return result


class TestAddContext(TestCase):
    def setUp(self):
        self.logzio_listener = listener.MockLogzioListener()
        self.logzio_listener.clear_logs_buffer()
        self.logzio_listener.clear_server_error()
        self.logs_drain_timeout = 1
        self.retries_no = 4
        self.retry_timeout = 2
        self.add_context = True
        self.logging_configuration = {
            "version": 1,
            "formatters": {
                "logzio": {
                    "format": '{"key": "value"}',
                    "validate": False
                }
            },
            "handlers": {
                "LogzioHandler": {
                    "class": "logzio.handler.LogzioHandler",
                    "formatter": "logzio",
                    "level": "DEBUG",
                    "token": "token",
                    'logzio_type': "type",
                    'logs_drain_timeout': self.logs_drain_timeout,
                    'url': "http://" + self.logzio_listener.get_host() + ":" + str(self.logzio_listener.get_port()),
                    'debug': True,
                    'retries_no': self.retries_no,
                    'retry_timeout': self.retry_timeout,
                    'add_context': self.add_context
                }
            },
            "loggers": {
                "test": {
                    "handlers": ["LogzioHandler"],
                    "level": "DEBUG"
                }
            }
        }

        logging.config.dictConfig(self.logging_configuration)
        self.logger = logging.getLogger('test')

        for curr_file in _find("logzio-failures-*.txt", "."):
            os.remove(curr_file)

    def test_add_context(self):
        # Logging configuration of add_context default to True
        log_message = "this log should have a trace context"
        self.logger.info(log_message)
        time.sleep(self.logs_drain_timeout * 2)
        logs_list = self.logzio_listener.logs_list
        for current_log in logs_list:
            if log_message in current_log:
                log_dict = json.loads(current_log)
                try:
                    self.assertTrue('otelSpanID' in log_dict)
                    self.assertTrue('otelTraceID' in log_dict)
                    self.assertTrue('otelServiceName' in log_dict)
                except AssertionError as err:
                    print(err)

    def test_ignore_context(self):
        # Set add_context to False and reconfigure the logger as it defaults to True
        self.logging_configuration["handlers"]["LogzioHandler"]["add_context"] = False
        logging.config.dictConfig(self.logging_configuration)
        self.logger = logging.getLogger('test')
        log_message = "this log should not have a trace context"
        self.logger.info(log_message)
        time.sleep(self.logs_drain_timeout * 2)
        logs_list = self.logzio_listener.logs_list
        for current_log in logs_list:
            if log_message in current_log:
                log_dict = json.loads(current_log)
                try:
                    self.assertFalse('otelSpanID' in log_dict)
                    self.assertFalse('otelTraceID' in log_dict)
                    self.assertFalse('otelServiceName' in log_dict)
                except AssertionError as err:
                    print(err)
