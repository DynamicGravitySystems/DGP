# coding: utf-8

import uuid
import functools
import collections

import numpy as np


def interp_nans(y):
    nans = np.isnan(y)
    x = lambda z: z.nonzero()[0]
    y[nans] = np.interp(x(nans), x(~nans), y[~nans])
    return y


def gen_uuid(prefix: str=''):
    """
    Generate a UUID4 String with optional prefix replacing the first len(prefix)
    characters of the UUID.

    Parameters
    ----------
    prefix : [str]
        Optional string prefix to be prepended to the generated UUID

    Returns
    -------
    str:
        UUID String of length 32
    """
    base_uuid = uuid.uuid4().hex
    return '{}{}'.format(prefix, base_uuid[len(prefix):])


def dispatch(type_=None):
    """
    @Decorator
    Pattern matching dispatcher of optional type constraint.
    This works similar to the single dispatch decorator in the Python
    functools module, however instead of dispatching based on type only,
    this provides a more general dispatcher that can operate based on value
    comparison.

    If type_ is specified, the registration function checks to ensure the
    registration value is of the appropriate type. Otherwise any value is
    permitted (as long as it is Hashable).

    """

    def dispatch_inner(base_func):
        dispatch_map = {}

        @functools.wraps(base_func)
        def wrapper(match, *args, **kwargs):
            # Strip args[0] off as match - delegated functions don't need it
            if match in dispatch_map:
                return dispatch_map[match](*args, **kwargs)

            return base_func(match, *args, **kwargs)

        def register(value):
            """
            register is a decorator which takes a parameter of the type
            specified in the dispatch() decorated method.

            The supplied enum value is then registered within the closures
            dispatch_map for execution by the base dispatch function.

            Parameters
            ----------
            value : type(type_)

            Returns
            -------

            """
            if not isinstance(value, collections.Hashable):
                raise ValueError("Registration value must be Hashable")
            if type_ is not None:
                if not isinstance(value, type_):
                    raise TypeError("Invalid dispatch registration type, "
                                    "must be of type {}".format(type_))
            elif isinstance(value, type):
                # Don't allow builtin type registrations e.g. float, must be
                # an instance of a builtin type (if there is no type_ declared)
                raise TypeError("Invalid registration value, must be an "
                                "instance, not an instance of type.")

            def register_inner(func):
                def reg_wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                dispatch_map[value] = reg_wrapper
                return reg_wrapper
            return register_inner

        wrapper.register = register
        return wrapper
    return dispatch_inner
