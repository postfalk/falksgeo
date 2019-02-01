from decimal import Decimal
import os
from zipfile import ZipFile
from affine import Affine
import fiona
import rasterio
from falksgeo import earthengine
from falksgeo.files import ensure_directory
from .base import DirectoryTestCase, TEST_RES_DIR, TEST_DATA_DIR


TEST_TMP_FILE = os.path.join(TEST_RES_DIR, 'tmp.zip')


def generate_shp_file(filename):
    schema = {'geometry': 'Polygon', 'properties':{}}
    args = (filename, 'w', 'ESRI Shapefile', schema)
    with fiona.open(*args, crs='epsg:4326') as out:
        out.write({
            'geometry': {
                'type': 'Polygon',
                'coordinates': [
                    [[-122, 38], [-122.01, 38], [-122.01, 38.01],
                     [-122, 38]]]
            },
            'properties': {}})


class TestHelpers(DirectoryTestCase):

    def moreSetUp(self):
        self.shp = os.path.join(TEST_RES_DIR, 'test.shp')
        generate_shp_file(self.shp)

    def test_generate_stitch_directory(self):
        earthengine.generate_stitch_directory(TEST_RES_DIR, 2.1)
        self.assertTrue(
            os.path.isdir(os.path.join(TEST_RES_DIR, '2_1')))

    def test_generate_path(self):
        res = earthengine.generate_path(
            TEST_RES_DIR, [[-122.666666, 43.0]], 2)
        self.assertEqual(
            res, os.path.join(TEST_RES_DIR, '2', 'EE_w122.666_43.0.tif'))
        res = earthengine.generate_path(
            TEST_RES_DIR, [[122.666666, 43.0]], 2)
        self.assertEqual(
            res, os.path.join(TEST_RES_DIR, '2', 'EE_122.6666_43.0.tif'))

    def test_generate_filename(self):
        res = earthengine.generate_filename([[122.666666, 43.023]])
        self.assertEqual(res, 'EE_122.6666_43.023.tif')
        res = earthengine.generate_filename([[122.666666, -43.023]])
        self.assertEqual(res, 'EE_122.6666_s43.023.tif')

    def test_region_from_shape(self):
        res = earthengine.region_from_shape(self.shp)
        self.assertEqual(
            res, [(-122.01, 38), (-122.01, 38.01), (-122, 38.01), (-122, 38)])

    def test_chunk_filter(self):
        region = [(
            -122.03, 38), (-122.03, 38.04), (-122, 38.04), (-122, 38)]
        chunks = earthengine.chunks_from_region(region)
        self.assertEqual(len(chunks), 4)
        res = earthengine.chunk_filter(chunks, self.shp)
        self.assertEqual(len(res), 2)

    def test_chunks_from_region(self):
        region = [(
            -122.03, 38), (-122.03, 38.04), (-122, 38.04), (-122, 38)]
        res = earthengine.chunks_from_region(region)
        self.assertEqual(len(res), 4)

    def test_floatrange(self):
        res = earthengine.floatrange(1, 10, .2)
        res = [item for item in res]
        self.assertEqual(len(res), 46)
        self.assertEqual(res[0], 1)
        self.assertAlmostEqual(res[-1], 10)

    def test_get_chunks(self):
        res = earthengine.get_chunks(self.shp, step=.006)
        self.assertEqual(len(res), 3)

    def test_chunks_to_shapefile(self):
        chunks = earthengine.get_chunks(self.shp, step=.006)
        chunk_shp_name = os.path.join(TEST_RES_DIR, 'chunks.shp')
        earthengine.chunks_to_shapefile(chunks, chunk_shp_name)
        self.assertTrue(os.path.isfile(chunk_shp_name))
        with fiona.open(chunk_shp_name) as collection:
            self.assertEqual(len(collection), 3)

    def test_get_tif_files(self):
        zipfilename = os.path.join(TEST_RES_DIR, 'testzipfile.zip')
        with ZipFile(zipfilename, 'w') as zip:
            for filename in ['test1.tif', 'test2.tif', 'test3.csv']:
                path = os.path.join(TEST_RES_DIR, filename)
                with open(path, 'w') as f:
                    f.write('something')
                zip.write(path, os.path.basename(path))
        with ZipFile(zipfilename) as zip:
            res = earthengine.get_tif_files(zip)
        self.assertEqual(len(res), 2)
        self.assertIn('test1.tif', res)
        self.assertIn('test2.tif', res)

    def test_new_profile(self):
        files_to_merge=[
            os.path.join(TEST_DATA_DIR, 'raster{}.tif'.format(ind))
            for ind in range(1, 4)]
        files = [rasterio.open(fn) for fn in files_to_merge]
        res = earthengine.new_profile(files)
        # TODO: develop better assertions
        self.assertEqual(
            res['transform'],
            Affine(0.00026949458523585647, 0.0, -122.01017003592595,
            0.0, -0.00026949458523585647, 38.012211247517556))


class TestDownloadParts(DirectoryTestCase):

    def moreSetUp(self):
        self.shp = os.path.join(TEST_RES_DIR, 'test.shp')
        generate_shp_file(self.shp)

    def test_download_parts(self):
        #TODO: use mocks here to speed tests up
        options = {'scale': 30, 'crs': 'EPSG:4326', 'region': None}
        res = earthengine.download_parts(
            self.shp, options, dest=TEST_RES_DIR, step=0.006)
        self.assertEqual(len(res), 3)
        for item in res:
            self.assertTrue(os.path.isfile(item))


class TestMerge(DirectoryTestCase):

    def test_merge(self):
        files_to_merge=[
            os.path.join(TEST_DATA_DIR, 'raster{}.tif'.format(ind))
            for ind in range(1, 4)]
        dest = os.path.join(TEST_RES_DIR, 'raster.tif')
        earthengine.merge(files_to_merge, dest)
        with rasterio.open(dest) as raster:
            self.assertEqual(raster.profile['height'], 46)
            self.assertEqual(raster.profile['width'], 46)


class TestDownloadImage(DirectoryTestCase):

    def test_download_image(self):
        region = [[-122, 38], [-122.01, 38], [-122.01, 38.01], [-122, 38.01]]
        options = {'scale': 30, 'crs': 'EPSG:4326', 'region': region}
        earthengine.download_image(options, TEST_TMP_FILE)
        self.assertTrue(os.path.isfile(TEST_TMP_FILE))
        with ZipFile(TEST_TMP_FILE) as zipf:
            zipf.extractall(TEST_RES_DIR)
        files = os.listdir(TEST_RES_DIR)
        tif = [item for item in files if '.tif' in item][0]
        with rasterio.open(os.path.join(TEST_RES_DIR, tif)) as img:
            self.assertEqual(img.height, 38)
            self.assertEqual(img.width, 38)
