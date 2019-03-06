import os
import sys
import shutil
import random
import string
from zipfile import ZipFile
import fiona
import fiona.crs
from shapely.geometry import shape, Point
from falksgeo import shapefile
from falksgeo.files import ensure_directory
from .base import DirectoryTestCase, TEST_RES_DIR, TEST_DATA_DIR


def create_shapefile(name='test.shp', rows=5, columns=6):
    """
    Create a shapefile for tests
    """
    crs = fiona.crs.from_epsg(3310)
    data = []
    cols = ['one', 'two', 'THREE', 'four', 'five', 'six', 'seven'][0:columns]
    schema = {'geometry': 'Point', 'properties': {k: 'str' for k in cols}}
    schema['properties']['number'] = 'int'
    kwargs = {'driver': 'ESRI Shapefile', 'schema': schema, 'crs': crs}
    with fiona.open(name, 'w', **kwargs) as f:
        for ind in range(0, rows):
            row = {'properties': {}}
            for item in cols:
                row['properties'][item] = (
                    ''.join(random.choices(string.ascii_lowercase, k=3)))
                row['properties']['number'] = ind % 4
                row['geometry'] = {'type': 'Point', 'coordinates': (ind, ind)}
            f.write(row)
    assert ind, rows-1


class TestCopyLayer(DirectoryTestCase):

    def moreSetUp(self):
        self.shapefile = os.path.join(TEST_RES_DIR, 'test.shp')
        self.outfile = os.path.join(TEST_RES_DIR, 'out.shp')
        create_shapefile(name=self.shapefile)

    def test_simple_copy(self):
        shapefile.copy_layer(self.shapefile, self.outfile)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            self.assertEqual(len(collection[1]['properties']), 7)
        # make sure it overwrites
        shapefile.copy_layer(self.shapefile, self.outfile)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            self.assertEqual(len(collection[1]['properties']), 7)

    def test_append(self):
        out = os.path.join(TEST_RES_DIR, 'appended.shp')
        shapefile.copy_layer(self.shapefile, out)
        shapefile.copy_layer(self.shapefile, out, append=True)
        with fiona.open(out) as collection:
            self.assertEqual(len(collection), 10)
            self.assertEqual(len(collection[1]['properties']), 7)

    def test_subset_cols(self):
        fields = ['one', 'THREE', 'four']
        shapefile.copy_layer(
            self.shapefile, self.outfile, fields=fields)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            self.assertEqual(len(collection[1]['properties']), 3)
            for field in fields:
                self.assertIn(field, collection[2]['properties'])
            for field in ['two', 'five', 'six', 'number']:
                self.assertNotIn(field, collection[3]['properties'])

    def test_remap(self):
        def remap(record):
            record['properties']['zwei'] = record['properties'].pop('two')
            return record
        shapefile.copy_layer(
             self.shapefile, self.outfile, remap_function=remap)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            fields = ['one', 'zwei', 'THREE', 'four', 'five', 'six', 'number']
            for field in fields:
                self.assertIn(field, collection[4]['properties'])
            self.assertNotIn('two', collection[0]['properties'])

    def test_filtering(self):
        def filtr(item, field=None, value=None):
            return item['properties'][field] == value
        shapefile.copy_layer(
            self.shapefile, self.outfile, filter_function=filtr,
            filter_kwargs={'field': 'number', 'value': 1})
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 2)
            for item in collection:
                self.assertIn(item['properties']['number'], [1, 3])

    def test_limit(self):
        shapefile.copy_layer(self.shapefile, self.outfile, limit=2)
        with fiona.open(self.outfile) as res:
            self.assertEqual(len([item for item in res]), 2)


class TestCopyShp(DirectoryTestCase):

    def moreSetUp(self):
        self.shapefile = os.path.join(TEST_RES_DIR, 'test.shp')
        self.outfile = os.path.join(TEST_RES_DIR, 'out.shp')
        create_shapefile(name=self.shapefile)

    def test_simple_copy(self):
        shapefile.copy_shp(self.shapefile, self.outfile)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            self.assertEqual(len(collection[1]['properties']), 7)
        # make sure it overwrites
        shapefile.copy_shp(self.shapefile, self.outfile)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            self.assertEqual(len(collection[1]['properties']), 7)

    def test_append(self):
        out = os.path.join(TEST_RES_DIR, 'appended.shp')
        shapefile.copy_shp(self.shapefile, out)
        shapefile.copy_shp(self.shapefile, out, append=True)
        with fiona.open(out) as collection:
            self.assertEqual(len(collection), 10)
            self.assertEqual(len(collection[1]['properties']), 7)

    def test_subset_cols(self):
        fields = ['one', 'THREE', 'four']
        shapefile.copy_shp(
            self.shapefile, self.outfile, fields=fields)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            self.assertEqual(len(collection[1]['properties']), 3)
            for field in fields:
                self.assertIn(field, collection[2]['properties'])
            for field in ['two', 'five', 'six', 'number']:
                self.assertNotIn(field, collection[3]['properties'])

    def test_remap(self):
        def remap(row):
            row['zwei'] = row['two']
            del row['two']
            return row
        shapefile.copy_shp(
             self.shapefile, self.outfile, remap_function=remap)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            fields = ['one', 'zwei', 'THREE', 'four', 'five', 'six', 'number']
            for field in fields:
                self.assertIn(field, collection[4]['properties'])
            self.assertNotIn('two', collection[0]['properties'])

    def test_filtering(self):
        def filtr(row):
            return row['number'] == 1
        shapefile.copy_shp(
            self.shapefile, self.outfile, filter_function=filtr)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 1)
            for item in collection:
                self.assertIn(item['properties']['number'], [1, 3])

    def test_crs(self):
        shapefile.copy_shp(self.shapefile, self.outfile)
        with fiona.open(self.outfile) as collection:
            self.assertEqual(collection.crs, {'init': 'epsg:3310'})

    def test_reproject(self):
        shapefile.copy_shp(self.shapefile, self.outfile, reproject=4326)
        with fiona.open(self.outfile) as collection:
            self.assertAlmostEqual(
                collection[0]['geometry']['coordinates'][0], -119.99999, 4)
            self.assertAlmostEqual(
                collection[0]['geometry']['coordinates'][1], 38.01636, 4)

    def test_reproject_with_remap(self):
        def remap(row):
            return row
        shapefile.copy_shp(
            self.shapefile, self.outfile, reproject=4326,
            remap_function=remap)
        with fiona.open(self.shapefile) as collection:
            self.assertEqual(collection.crs, {'init': 'epsg:3310'})

    def test_sort(self):
        with fiona.open(self.shapefile) as collection:
            values = [item['properties']['one'] for item in collection]
            unsorted = values.copy()
            values.sort()
            self.assertNotEqual(unsorted, values)
        shapefile.copy_shp(self.shapefile, self.outfile, sort=['one'])
        with fiona.open(self.outfile) as collection:
            values = [item['properties']['one'] for item in collection]
            unsorted = values.copy()
            values.sort()
            self.assertEqual(unsorted, values)


class TestAnnotateFile(DirectoryTestCase):

    def moreSetUp(self):
        self.infile = os.path.join(TEST_RES_DIR, 'in.shp')
        self.outfile = os.path.join(TEST_RES_DIR, 'out.shp')
        create_shapefile(self.infile)
        self.csv = os.path.join(TEST_RES_DIR, 'annotation.csv')
        with open(self.csv, 'w') as csv:
            csv.write('number,value\n0,sad\n1,solala\n2, happy')

    def test_annotate_file(self):
        shapefile.annotate_file(
            [self.infile, self.csv], self.outfile, index='number')
        with fiona.open(self.outfile) as collection:
            self.assertEqual(len(collection), 5)
            for item in collection:
                props = item['properties']
                print(props['number'], props['value'])
                assertions = ['sad', 'solala', 'happy', None]
                props = item['properties']
                self.assertEqual(assertions[props['number']], props['value'])


class TestCSVToShapefile(DirectoryTestCase):

    def moreSetUp(self):
        self.csv_fn = os.path.join(TEST_RES_DIR, 'test.csv')
        self.shp_fn = os.path.join(TEST_RES_DIR, 'res.shp')
        with open(self.csv_fn, 'w') as csv:
            csv.write('name,x,y\nlittle house,-125,25\nbig house,-125.1,25')

    def test_csv_to_shapefile(self):
        shapefile.csv_to_shp(self.csv_fn, self.shp_fn)
        with fiona.open(self.shp_fn) as collection:
            self.assertEqual(len(collection), 2)
            self.assertEqual(
                collection.schema, {
                    'geometry': 'Point',
                    'properties': {'name': 'str:80'}})
            self.assertEqual(collection.driver, 'ESRI Shapefile')
            self.assertEqual(collection.crs, {'init': 'epsg:4326'})


class TestZipShapefile(DirectoryTestCase):

    def moreSetUp(self):
        self.shp = os.path.join(TEST_RES_DIR, 'forzipping.shp')
        create_shapefile(self.shp)

    def test_zip_shapefile(self):
        zipfilename = shapefile.zip_shp(self.shp)
        self.assertEqual(
            zipfilename, os.path.join(TEST_RES_DIR, 'forzipping.zip'))
        with ZipFile(zipfilename) as zipf:
            for item in ['dbf', 'shp', 'prj', 'shx']:
                name = '.'.join([os.path.basename(self.shp)[:-4], item])
                self.assertIn(name, zipf.namelist())
