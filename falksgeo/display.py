"""
Helpers to display action and progress
"""

import sys
from functools import wraps


class PercentDisplay(object):
    """
    Display progress in a loop
    """

    def __init__(self, collection, count=None, percent_step=1, debug=None):
        self.count = len(collection) if collection else count
        self.brk = int(self.count/100*percent_step) + 1
        self.counter = 0
        self.debug = debug
        self.display()

    def display(self):
        sys.stdout.write(
            ''.join([str(int(self.counter/self.count * 100)), '%', '\r']))
        sys.stdout.flush()

    def check_debug(self):
        if self.debug and self.debug < self.counter:
            raise StopIteration

    def inc(self):
        self.counter += 1
        self.check_debug()
        if not self.counter % self.brk:
            self.display()


def print_docstring(f, *args, **kwargs):
    """
    Decorator: print the doc string of a function before execution
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        snippet = f.__doc__.strip() if f.__doc__ else f.__name__
        print('\n', snippet, '\n', sep='')
        return f(*args, **kwargs)
    return decorated
