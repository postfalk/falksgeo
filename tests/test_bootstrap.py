import os
import shutil
from unittest import TestCase
from falksgeo import bootstrap
from falksgeo.files import ensure_directory
from .base import DirectoryTestCase, TEST_RES_DIR


TEST_A_DIR = os.path.join(TEST_RES_DIR, 'adir')
TEST_B_DIR = os.path.join(TEST_RES_DIR, 'bdir')
TEST_FILENAME = os.path.join(TEST_A_DIR, 'testfile.csv')
TEST_RES_FILENAME = os.path.join(TEST_RES_DIR, 'bdir', 'testfile.csv')


class TestCheckOrCreateFile(DirectoryTestCase):

    def moreSetUp(self):
        ensure_directory(TEST_A_DIR)
        with open(TEST_FILENAME, 'w') as tf:
            tf.write('0,0,0,0')

    def test_copy_tree(self):
        bootstrap.check_or_create_files(
            TEST_A_DIR, TEST_RES_FILENAME,
            create_kwargs={'directory': TEST_B_DIR})
        bootstrap.check_or_create_files(
            TEST_A_DIR, TEST_RES_FILENAME,
            create_kwargs={'directory': TEST_B_DIR})
