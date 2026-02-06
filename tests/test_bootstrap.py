# pylint:disable=C0103,C0114,C0115,C0116,W0511,E0401
# standard library
import os
from time import sleep
from copy import copy
# third party
import fiona
# local
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
        with open(TEST_FILENAME, 'w', encoding='utf-8') as handle:
            handle.write('0,0,0,0')

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
        with open(TEST_FILENAME, 'w', encoding='utf-8') as tf:
            tf.write('0,0,0,0')
        with open(ANOTHER_TEST_FILENAME, 'w', encoding='utf-8') as tf:
            tf.write('bla')

    def test_hash_file(self):
        self.assertEqual(
            bootstrap.hash_file(TEST_FILENAME),
            '886364986cd9a5c816240f0512f36bee')
        with open(TEST_FILENAME, 'a', encoding='utf-8') as fil:
            fil.write('test')
        # make sure we hash the content and not the filename
        self.assertEqual(
            bootstrap.hash_file(TEST_FILENAME),
            'd33cdfbc66e23a13a5844cbf12794352')

    def test_shapefilebehavior(self):
        """
        This is not really a test but confirms suspected behavior that
        hashing on .shp part of shapefiles does not capture attribute
        changes.
        """
        schema = {'geometry': 'Point', 'properties': {'test': 'str'}}
        args = TEST_SHAPEFILE, 'w', 'ESRI Shapefile', schema
        with fiona.open(*args) as fil:
            fil.write({
                'geometry': {'type': 'Point', 'coordinates': [1, 1]},
                'properties': {'test': 'cat'}})
        myhash = bootstrap.hash_file(TEST_SHAPEFILE)
        with fiona.open(TEST_SHAPEFILE) as collection:
            args = TEST_SHAPEFILE_1, 'w', 'ESRI Shapefile', schema
            with fiona.open(*args) as new_collection:
                for item in collection:
                    new_item = fiona.Feature(
                        geometry = copy(item.geometry),
                        properties = fiona.Properties.from_dict({'test': 'dog'})
                    )
                    new_collection.write(new_item)
        # for a working hash algorithm that should be not equal!
        self.assertEqual(myhash, bootstrap.hash_file(TEST_SHAPEFILE_1))
        with fiona.open(TEST_SHAPEFILE) as collection:
            args = TEST_SHAPEFILE_1, 'w', 'ESRI Shapefile', schema
            with fiona.open(*args) as new_collection:
                for item in collection:
                    new_item = fiona.Feature(
                        geometry = fiona.Geometry.from_dict({
                            'type': 'Point', 'coordinates': [3, 3]}),
                        properties = copy(item.properties))
                    new_collection.write(new_item)
        self.assertNotEqual(myhash, bootstrap.hash_file(TEST_SHAPEFILE_1))


class TestChangeTracking(DirectoryTestCase):

    def moreSetUp(self):
        try:
            os.remove(TEST_HASH_STORE)
        except FileNotFoundError:
            pass
        ensure_directory(TEST_A_DIR)
        with open(TEST_FILENAME, 'w', encoding='utf-8') as handle:
            handle.write('0,0,0,0')
        with open(ANOTHER_TEST_FILENAME, 'w', encoding='utf-8') as handle:
            handle.write('bla')
        schema = {'geometry': 'Point', 'properties': {'test': 'str'}}
        args = TEST_SHAPEFILE, 'w', 'ESRI Shapefile', schema
        with fiona.open(*args) as shp:
            shp.write({
                'geometry': {'type': 'Point', 'coordinates': [1, 1]},
                'properties': {'test': 'dog'}})

    def test_shapefile_changes(self):
        try:
            os.remove(TEST_HASH_STORE)
        except FileNotFoundError:
            pass
        self.assertFalse(bootstrap.check_source_changes(
            TEST_SHAPEFILE, hash_store_name=TEST_HASH_STORE))
        self.assertFalse(bootstrap.check_source_changes(
            TEST_SHAPEFILE, hash_store_name=TEST_HASH_STORE))
        schema = {'geometry': 'Point', 'properties': {'test': 'str'}}
        args = TEST_SHAPEFILE, 'w', 'ESRI Shapefile', schema
        with fiona.open(TEST_SHAPEFILE) as collection:
            data = list(collection)
        with fiona.open(*args) as new_collection:
            for item in data:
                new_collection.write(item)
        self.assertTrue(bootstrap.check_source_changes(
            TEST_SHAPEFILE, hash_store_name=TEST_HASH_STORE))

    def test_source_change(self):
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
        with open(TEST_FILENAME, 'a', encoding='utf-8') as fil:
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
        sleep(1)
        with open(ANOTHER_TEST_FILENAME, 'w', encoding='utf-8') as fil:
            fil.write('hello world')
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
