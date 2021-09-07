# pylint:disable=C0114,C0115,C0116
# standard library
import logging
from unittest import TestCase
# project
# from falksgeo import arcgis


logging.basicConfig()
logging.getLogger().setLevel(logging.CRITICAL)


# class TestGetGis(TestCase):
#
#     gis = arcgis.get_gis(
#        'https://www.arcgis.com', 'arcgis_python', 'P@ssword123')
#        self.assertEqual(
#            str(gis), 'GIS @ https://geosaurus.maps.arcgis.com version:8.4')
