# pylint:disable=C0103,C0114,C0115,C0116
# standard library
import logging
import os
import shutil
from unittest import TestCase

logging.basicConfig()
logging.getLogger().setLevel(logging.CRITICAL)


TESTDIR = os.path.abspath(os.path.dirname(__file__))
TEST_RES_DIR = os.path.join(TESTDIR, 'testres')
TEST_DATA_DIR = os.path.join(TESTDIR, 'testdata')


class DirectoryTestCase(TestCase):
    delete = True

    def moreSetUp(self):
        pass

    def setUp(self):
        os.makedirs(TEST_RES_DIR, exist_ok=True)
        self.moreSetUp()

    def tearDown(self):
        if self.delete:
            shutil.rmtree(TEST_RES_DIR)
