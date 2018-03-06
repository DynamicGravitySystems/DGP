# coding=utf-8

from pandas import DataFrame
import inspect
from functools import wraps

from dgp.lib.etc import gen_uuid, dedup_dict


transform_registry = {}


def createtransform(func):
    """
    Function decorator that generates a transform class for the decorated
    function.

    This decorator is an alternative to defining a subclass of Transform.
    The class generated by this decorator is automatically inserted into the
    transform registry.

    Positional arguments are reserved for data.
    Required keyword arguments are made into attributes of the class.

    Returns
    -------
    Transform
        A callable instance of a class that subclasses Transform
    """

    def class_func(self, *args, **kwargs):
        return func(*args, **kwargs)

    sig = inspect.signature(func)
    class_id = func.__name__
    cls = type(class_id, (Transform,),
               dict(func=class_func, _sig=sig))
    transform_registry[class_id] = cls

    @wraps(func)
    def wrapper(*args, **kwargs):
        return cls(*args, **kwargs)

    return wrapper


def register_transform_class(cls):
    """
    Class decorator for constructing transform classes.

    The decorator adds an entry for the decorated class into the transform
    class registry.
    """
    class_id = cls.__name__
    if class_id in transform_registry:
        raise KeyError('Transform class {cls} already exists in registry.'
                       .format(cls=class_id))

    transform_registry[class_id] = cls
    return cls


class Transform:
    """
    Transform base class.

    All transform classes should subclass this one.

    The class instance is callable. When a class instance is called, all of the
    variables specified in the function signature must have a value, otherwise
    a ValueError will be raised.

    There are three ways to specify and set values for variables used by the
    function:
        - in the function signature
        - as keyword arguments with values when instantiating the class
        - as keywords when the instance is called

    In all cases, variables are made into attributes of the class set with
    the values specified.

    Additional variables can be added as attributes (as metadata, for example)
    of the class by passing the names and values as keyword arguments when
    instantiating the class.
    """

    def __init__(self, **kwargs):
        self._uid = gen_uuid('tf')
        self._var_list = []

        if getattr(self, '_sig', None) is None:
            self._sig = inspect.signature(self.func)

        for param in self._sig.parameters.values():
            if param.kind == param.KEYWORD_ONLY and getattr(self, param.name, None) is None:
                if param.default is not param.empty:
                    setattr(self, param.name, param.default)
                self._var_list.append(param.name)

        # add attributes not explicitly used by the function
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def uid(self):
        return self._uid

    def __call__(self, *args, **kwargs):
        keywords = {name: self.__dict__[name] for name in self._var_list
                    if name in self.__dict__}

        # override keywords explicitly set in function call
        for k, v in kwargs.items():
            if getattr(self, k, None) is None:
                setattr(self, k, v)

            keywords[k] = v

        # check whether all attributes have values set
        notset = []
        for name in self._var_list:
            if name not in keywords:
                notset.append(name)

        if notset:
            raise ValueError('Required attributes not set: {attr}'
                             .format(attr=', '.join(notset)))

        return self.func(*args, **keywords)

    def __str__(self):
        attrs = ', '.join(['{var}={val}'.format(var=k, val=v)
                           for k, v in [(var, self.__dict__[var])
                                        for var in self._var_list]])
        return '{cls}({attrs})'.format(cls=self.__class__.__name__,
                                       attrs=attrs)


class DataWrapper:
    """
    A container for transformed DataFrames. Multiple transform chains may
    be specified and the resultant DataFrames will be held in this class
    instance.
    """
    def __init__(self, frame: DataFrame):
        self.df = frame # original DataFrame; not ever modified
        self.modified = {}
        self._transform_chains = {}
        self._defaultchain = None

    def removechain(self, uid):
        del self._transform_chains[uid]
        del self.modified[uid]

    def applychain(self, tc):
        if not isinstance(tc, TransformChain):
            raise TypeError('expected an instance or subclass of '
                            'TransformChain, but got {typ}'
                            .format(typ=type(tc)))

        if tc.uid not in self._transform_chains:
            self._transform_chains[tc.uid] = tc
            if self._defaultchain is None:
                self._defaultchain = self._transform_chains[tc.uid]
        self.modified[tc.uid] = self._transform_chains[tc.uid].apply(self.df)
        return self.modified[tc.uid]

    @property
    def data(self, reapply=False):
        if self._defaultchain is not None:
            if reapply:
                return self.applychain(self._defaultchain)
            else:
                return self.modified[self._defaultchain.uid]
        else:
            return self.df

    def __len__(self):
        return len(self.modified.items())