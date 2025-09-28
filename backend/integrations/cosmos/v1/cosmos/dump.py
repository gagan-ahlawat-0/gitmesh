"""
Simple dump function for debugging purposes.
"""

def dump(*args, **kwargs):
    """
    Simple dump function for debugging.
    Prints the arguments in a readable format.
    """
    import pprint
    for arg in args:
        pprint.pprint(arg)
    if kwargs:
        pprint.pprint(kwargs)