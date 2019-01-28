"""
Functions requiring Pandas or GeoPandas
"""
import geopandas
import pandas as pd
from .transformations import camel_to_snake


def normalize_pandas_cols(df):
    """
    Normalize the column names of a pandas dataframe
    """
    lst = list(df)
    dic = {item:camel_to_snake(item)[:10] for item in lst}
    dic['ComID'] = 'comid'
    ndf = df.rename(columns=dic)
    return ndf


def concat_dataframes(filenames):
    """
    Create a single dataframe from several sources with (nearly) identical
    schema.
    """
    for index, filename in enumerate(filenames):
        print('Reading {}'.format(filename))
        df = normalize_pandas_cols(geopandas.read_file(filename))
        ndf = pd.concat([ndf, df]) if index else df
    ndf.set_index('comid')
    # reading with GeoPandas generates an (empty) geometry
    # that would conflict down the road, hence dropping it
    return ndf.drop('geometry', axis=1)
