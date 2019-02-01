import os
import shutil
from unittest import TestCase
from falksgeo.files import ensure_directory


TESTDIR = os.path.abspath(os.path.dirname(__file__))
TEST_RES_DIR = os.path.join(TESTDIR, 'testres')
TEST_DATA_DIR = os.path.join(TESTDIR, 'testdata')


class DirectoryTestCase(TestCase):
    delete = True

    def moreSetUp(self):
        pass

    def setUp(self):
        ensure_directory(TEST_RES_DIR)
        self.moreSetUp()

    def tearDown(self):
        if self.delete:
            shutil.rmtree(TEST_RES_DIR)
