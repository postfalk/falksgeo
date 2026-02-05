"""
Diverse mapping functions in support of tools
"""
import re


# see
# https://gist.github.com/jaytaylor/3660565#file-camel_case_to_snake_case-py-L17
_underscorer1 = re.compile(r'(.)([A-Z][a-z]+)')
_underscorer2 = re.compile('([a-z0-9])([A-Z])')


def camel_to_snake(s):
    """
    Convert camel case strings to underscore
    """
    subbed = _underscorer1.sub(r'\1_\2', s)
    return _underscorer2.sub(r'\1_\2', subbed).lower()


def empty(item:dict, schema:bool=False) -> dict:
    """
    Placeholder function to pass along instead of transformations
    """
    del schema
    return item


def calculate_display_value(record):
    """
    Logic for display values
    """
    if record['ds_max_flo'] and not record['ds_max_flo'] == 'None':
        if float(record['ds_max_flo']) > 300:
            return 1
        if float(record['ds_max_flo']) > 100:
            return 2
        if float(record['ds_max_flo']) > 10:
            return 3
    return 4
