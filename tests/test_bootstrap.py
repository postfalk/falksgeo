import os
import shutil
from unittest import TestCase
import fiona
from falksgeo import bootstrap
from falksgeo.files import ensure_directory
from .base import DirectoryTestCase, TEST_RES_DIR


TEST_A_DIR = os.path.join(TEST_RES_DIR, 'adir')
TEST_B_DIR = os.path.join(TEST_RES_DIR, 'bdir')
TEST_FILENAME = os.path.join(TEST_A_DIR, 'testfile.csv')
ANOTHER_TEST_FILENAME = os.path.join(TEST_A_DIR, 'anothertestfile.csv')
TEST_RES_FILENAME = os.path.join(TEST_RES_DIR, 'bdir', 'testfile.csv')
TEST_HASH_STORE = os.path.join(TEST_RES_DIR, 'hashes.json')
TEST_SHAPEFILE = os.path.join(TEST_RES_DIR, 'test.shp')
TEST_SHAPEFILE_1 = os.path.join(TEST_RES_DIR, 'test1.shp')


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

    def test_shapefilebehavior(self):
        schema = {'geometry': 'Point', 'properties': {'test': 'str'}}
        args = TEST_SHAPEFILE, 'w', 'ESRI Shapefile', schema
        with fiona.open(*args) as fil:
            fil.write({
                'geometry': {'type': 'Point', 'coordinates': [1, 1]},
                'properties': {'test': 'cat'}})
        print(bootstrap.hash_file(TEST_SHAPEFILE))
        with fiona.open(TEST_SHAPEFILE) as collection:
            args = TEST_SHAPEFILE_1, 'w', 'ESRI Shapefile', schema
            with fiona.open(*args) as new_collection:
                for item in collection:
                    item['properties']['test'] = 'dog'
                    item['geometry'] = {
                        'type': 'Point', 'coordinates': [3, 3]}
                    new_collection.write(item)
        print(bootstrap.hash_file(TEST_SHAPEFILE_1))


class TestChangeTracking(DirectoryTestCase):

    def moreSetUp(self):
        ensure_directory(TEST_A_DIR)
        with open(TEST_FILENAME, 'w') as tf:
            tf.write('0,0,0,0')
        with open(ANOTHER_TEST_FILENAME, 'w') as tf:
            tf.write('bla')

    def test_source_changes(self):
        # source change False if no hash file provided
        self.assertFalse(bootstrap.check_source_changes(TEST_FILENAME))
        self.assertFalse(bootstrap.check_source_changes(TEST_FILENAME))
        # source change True if no hash file provided but
        # no_hast_store_default set to True
        self.assertTrue(bootstrap.check_source_changes(
            TEST_FILENAME, no_hash_store_default=True))

    def test_hashfile_creation(self):
        # creation should not be run if hash file does not exist
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))

    def test_hashfile_creation_with_option(self):
        # creation should be run if hash file does exist
        self.assertTrue(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE,
            key_not_exist_default=True))
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE,
            key_not_exist_default=True))

    def test_regular_file_change(self):
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))
        with open(TEST_FILENAME, 'a') as fil:
            fil.write('ha')
        self.assertTrue(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            TEST_FILENAME, hash_store_name=TEST_HASH_STORE))

    def test_list(self):
        test_list = [TEST_FILENAME, ANOTHER_TEST_FILENAME]
        self.assertFalse(bootstrap.check_source_changes(
            test_list, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            test_list, hash_store_name=TEST_HASH_STORE))
        with open(ANOTHER_TEST_FILENAME, 'a') as fil:
            fil.write('hello')
        self.assertTrue(bootstrap.check_source_changes(
            test_list, hash_store_name=TEST_HASH_STORE))

    def test_ignore_non_files(self):
        # if we decide to not track then we can also reload
        # non-trackable resources
        self.assertTrue(bootstrap.check_source_changes(
            'https://google.com', no_hash_store_default=True))
        # if the source is untrackable we should not able to force
        # it to reload because the key is absent
        self.assertFalse(bootstrap.check_source_changes(
            'https://google.com', hash_store_name=TEST_HASH_STORE,
            key_not_exist_default=True))
        self.assertFalse(bootstrap.check_source_changes(
            'https://google.com', hash_store_name=TEST_HASH_STORE,
            key_not_exist_default=True))
