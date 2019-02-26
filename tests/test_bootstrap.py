import os
import shutil
from unittest import TestCase
from falksgeo import bootstrap
from falksgeo.files import ensure_directory
from .base import DirectoryTestCase, TEST_RES_DIR


TEST_A_DIR = os.path.join(TEST_RES_DIR, 'adir')
TEST_B_DIR = os.path.join(TEST_RES_DIR, 'bdir')
TEST_FILENAME = os.path.join(TEST_A_DIR, 'testfile.csv')
ANOTHER_TEST_FILENAME = os.path.join(TEST_A_DIR, 'anothertestfile.csv')
TEST_RES_FILENAME = os.path.join(TEST_RES_DIR, 'bdir', 'testfile.csv')
TEST_HASH_STORE = os.path.join(TEST_RES_DIR, 'hashes.json')


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


class TestHashing(DirectoryTestCase):

    def moreSetUp(self):
        ensure_directory(TEST_A_DIR)
        with open(TEST_FILENAME, 'w') as tf:
            tf.write('0,0,0,0')
        with open(ANOTHER_TEST_FILENAME, 'w') as tf:
            tf.write('bla')

    def test_hash_file(self):
        self.assertEqual(
            bootstrap.hash_file(TEST_FILENAME),
            '886364986cd9a5c816240f0512f36bee')
        with open(TEST_FILENAME, 'a') as fil:
            fil.write('test')
        # make sure we hash the content and not the filename
        self.assertEqual(
            bootstrap.hash_file(TEST_FILENAME),
            'd33cdfbc66e23a13a5844cbf12794352')

    def test_source_changes(self):
        # source change always True if no hash file provided
        self.assertFalse(bootstrap.check_source_changes(TEST_FILENAME))
        self.assertFalse(bootstrap.check_source_changes(TEST_FILENAME))
        self.assertTrue(bootstrap.check_source_changes(
            TEST_FILENAME, no_hash_store_default=True))
        # source should be written to the hash file
        self.assertTrue(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))
        # test providing a list of upstream sources
        test_list = [TEST_FILENAME, ANOTHER_TEST_FILENAME]
        self.assertTrue(bootstrap.check_source_changes(
            test_list, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            test_list, hash_store_name=TEST_HASH_STORE))
        with open(ANOTHER_TEST_FILENAME, 'a') as fil:
            fil.write('hello')
        self.assertTrue(bootstrap.check_source_changes(
            test_list, hash_store_name=TEST_HASH_STORE))
        # test with URL's to ignore (in order to not download entire files
        # for hashing)
        self.assertFalse(bootstrap.check_source_changes(
            'https://google.com', hash_store_name=TEST_HASH_STORE))
