# coding: utf-8

import uuid
import functools
import collections

import numpy as np


def align_frames(frame1, frame2, align_to='left', interp_method='time',
                 interp_only=[], fill={}):
    # TODO: Is there a more appropriate place for this function?
    # TODO: Add ability to specify interpolation method per column.
    # TODO: Ensure that dtypes are preserved unless interpolated.
    """
    Align and crop two objects

    Parameters
    ----------
    frame1: :obj:`DataFrame` or :obj:`Series
        Must have a time-like index
    frame1: :obj:`DataFrame` or :obj:`Series
        Must have a time-like index
    align_to: {'left', 'right'}, :obj:`DatetimeIndex`
        Index to which data are aligned.
    interp_method: {‘linear’, ‘time’, ‘index’, ‘values’, ‘nearest’, ‘zero’,
    ‘slinear’, ‘quadratic’, ‘cubic’, ‘barycentric’, ‘krogh’, ‘polynomial’,
    ‘spline’, ‘piecewise_polynomial’, ‘from_derivatives’, ‘pchip’, ‘akima’}
        - ‘linear’: ignore the index and treat the values as equally spaced.
           This is the only method supported on MultiIndexes.
        - ‘time’: interpolation works on daily and higher resolution data to
           interpolate given length of interval. default
        - ‘index’, ‘values’: use the actual numerical values of the index
        - ‘nearest’, ‘zero’, ‘slinear’, ‘quadratic’, ‘cubic’, ‘barycentric’,
          ‘polynomial’ is passed to scipy.interpolate.interp1d. Both
          ‘polynomial’ and ‘spline’ require that you also specify an order
          (int), e.g. df.interpolate(method=’polynomial’, order=4). These
          use the actual numerical values of the index.
        - ‘krogh’, ‘piecewise_polynomial’, ‘spline’, ‘pchip’ and ‘akima’ are
           all wrappers around the scipy interpolation methods of similar
           names. These use the actual numerical values of the index.
           For more information on their behavior, see the scipy
           documentation and tutorial documentation
        - ‘from_derivatives’ refers to BPoly.from_derivatives which replaces
          ‘piecewise_polynomial’ interpolation method in scipy 0.18
    interp_only: set or list
        If empty, then all columns except for those indicated in `fill` are
        interpolated. Otherwise, only columns listed here are interpolated.
        Any column not interpolated and not listed in `fill` is filled with
        `ffill`.
    fill: dict
        Indicate which columns are not to be interpolated.  Available fill
        methods are {'bfill', 'ffill', None}, or specify a value to fill.
        If a column is not present in the dictionary, then it will be
        interpolated.

    Returns
    -------
    (frame1, frame2)
        Aligned and cropped objects

    Raises
    ------
    ValueError
        When frames do not overlap, and if an incorrect `align_to` argument
        is given.
    """
    def fill_nans(frame):
        # TODO: Refactor this function to be less repetitive
        if hasattr(frame, 'columns'):
            for column in frame.columns:
                if interp_only:
                    if column in interp_only:
                        frame[column] = frame[column].interpolate(method=interp_method)
                    elif column in fill.keys():
                        if fill[column] in ('bfill', 'ffill'):
                            frame[column] = frame[column].fillna(method=fill[column])
                        else:
                            # TODO: Validate value
                            frame[column] = frame[column].fillna(value=fill[column])
                    else:
                        frame[column] = frame[column].fillna(method='ffill')
                else:
                    if column not in fill.keys():
                        frame[column] = frame[column].interpolate(method=interp_method)
                    else:
                        if fill[column] in ('bfill', 'ffill'):
                            frame[column] = frame[column].fillna(method=fill[column])
                        else:
                            # TODO: Validate value
                            frame[column] = frame[column].fillna(value=fill[column])
        else:
            frame = frame.interpolate(method=interp_method)
        return frame

    if align_to not in ('left', 'right'):
        raise ValueError('Invalid value for align_to parameter: {val}'
                         .format(val=align_to))

    if frame1.index.min() >= frame2.index.max() \
            or frame1.index.max() <= frame2.index.min():
        raise ValueError('Frames do not overlap')

    if align_to == 'left':
        new_index = frame1.index
    elif align_to == 'right':
        new_index = frame2.index

    left, right = frame1.align(frame2, axis=0, copy=True)

    left = fill_nans(left)
    right = fill_nans(right)

    left = left.reindex(new_index).dropna()
    right = right.reindex(new_index).dropna()

    # crop frames
    if left.index.min() > right.index.min():
        begin = left.index.min()
    else:
        begin = right.index.min()

    if left.index.max() < right.index.max():
        end = left.index.max()
    else:
        end = right.index.max()

    left = left.loc[begin:end]
    right = right.loc[begin:end]

    return left, right


def interp_nans(y):
    # TODO: SettingWithCopyWarning
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
