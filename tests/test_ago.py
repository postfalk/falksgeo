from unittest import TestCase
from falksgeo import arcgis


import logging
logging.basicConfig()
logging.getLogger().setLevel(logging.CRITICAL)


class TestGetGis(TestCase):

    def test_get_gis(self):
        gis = arcgis.get_gis(
            'https://www.arcgis.com', 'arcgis_python', 'P@ssword123')
        self.assertEqual(
            str(gis), 'GIS @ https://geosaurus.maps.arcgis.com version:6.4')
