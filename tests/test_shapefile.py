from unittest import TestCase
import os
import sys
import shutil
import random
import string
import fiona
import fiona.crs
from shapely.geometry import shape, Point
from falksgeo import shapefile
from falksgeo.files import ensure_directory


TMP_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'testdata'))


def create_shapefile(name='test.shp', rows=5, columns=6):
    """
    Create a shapefile for tests
    """
    crs = fiona.crs.from_epsg(4326)
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
                row['properties']['number'] = ind % 2
                row['geometry'] = {'type': 'Point', 'coordinates': (ind, ind)}
            f.write(row)
    assert ind, rows-1


class TestCopyLayer(TestCase):

    def setUp(self):
        ensure_directory(TMP_FOLDER)
        self.shapefile = os.path.join(TMP_FOLDER, 'test.shp')
        self.outfile = os.path.join(TMP_FOLDER, 'out.shp')
        create_shapefile(name=self.shapefile)

    def tearDown(self):
        shutil.rmtree(TMP_FOLDER)

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
        out = os.path.join(TMP_FOLDER, 'appended.shp')
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


class TestCSVToShapefile(TestCase):

    def setUp(self):
        ensure_directory(TMP_FOLDER)
        self.csv_fn = os.path.join(TMP_FOLDER, 'test.csv')
        self.shp_fn = os.path.join(TMP_FOLDER, 'res.shp')
        with open(self.csv_fn, 'w') as csv:
            csv.write('name,x,y\nlittle house,-125,25\nbig house,-125.1,25')

    def tearDown(self):
        shutil.rmtree(TMP_FOLDER)

    def test_csv_to_shapefile(self):
        shapefile.csv_to_shapefile(self.csv_fn, self.shp_fn)
        with fiona.open(self.shp_fn) as collection:
            self.assertEqual(len(collection), 2)
            self.assertEqual(
                collection.schema, {
                    'geometry': 'Point',
                    'properties': {'name': 'str:80'}})
            self.assertEqual(collection.driver, 'ESRI Shapefile')
            self.assertEqual(collection.crs, {'init': 'epsg:4326'})

