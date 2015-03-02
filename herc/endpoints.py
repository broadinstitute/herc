from collections import OrderedDict
import inspect

def prettify(endpoint_mapping):
    """Constructs a dict of endpoints and their descriptions, pulled from the docstrings of the endpoint classes themselves."""
    http_methods = ['get', 'post', 'put', 'patch']  # others?

    # for each endpoint, get the methods of its associated RequestHandler class that are explicitly defined in said class and are in http_methods
    # the docstring for the methods has its friendly format as the first line, and a description after that.
    # they end up looking like { "GET /schema": "Returns the JSON schema used to validate job submission requests." }
    d = {inspect.getdoc(meth).split('\n', 1)[0]: inspect.getdoc(meth).split('\n', 1)[-1]
         for end in endpoint_mapping.values()
         for (mname, meth) in inspect.getmembers(end['class'], lambda m: inspect.isfunction(m)
                                                 and m.__name__ in end['class'].__dict__
                                                 and m.__name__ in http_methods)}
    return OrderedDict(sorted(d.items(), key=lambda t: t[0]))
