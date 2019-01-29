import os
import shutil
from unittest import TestCase
from falksgeo import bootstrap
from falksgeo.files import ensure_directory


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_SUB_DIR = os.path.join(TEST_DIR, 'adir')
TEST_RES_DIR = os.path.join(TEST_DIR, 'bdir')
TEST_FILENAME = os.path.join(TEST_SUB_DIR, 'testfile.csv')
TEST_RES_FILENAME = os.path.join(TEST_DIR, 'bdir', 'testfile.csv')
TEST_ASSETS = (TEST_SUB_DIR, TEST_RES_DIR)


class TestCheckOrCreateFile(TestCase):

    def setUp(self):
        ensure_directory(TEST_SUB_DIR)
        with open(TEST_FILENAME, 'w') as tf:
            tf.write('0,0,0,0')

    def tearDown(self):
        for item in TEST_ASSETS:
            try:
                shutil.rmtree(item)
            except FileNotFoundError:
                pass

    def test_copy_tree(self):
        try:
            shutil.rmtree(TEST_RES_DIR)
        except FileNotFoundError:
            pass
        bootstrap.check_or_create_files(
            TEST_SUB_DIR, TEST_RES_FILENAME,
            create_kwargs={'directory': os.path.join(TEST_DIR, 'bdir')})
        bootstrap.check_or_create_files(
            TEST_SUB_DIR, TEST_RES_FILENAME,
            create_kwargs={'directory': os.path.join(TEST_DIR, 'bdir')})
