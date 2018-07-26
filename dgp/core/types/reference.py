# -*- coding: utf-8 -*-


class Reference:
    """Reference is a simple wrapper class designed to facilitate object
    references within the DGP project models. This is necessary due to the
    nature of the project's JSON serialization/de-serialization protocol, as the
    JSON standard does not allow cyclical links (where some object makes
    reference to another object that has already been encoded).

    Parameters
    ----------
    owner :
        Owner of this reference, must have a 'uid' attribute and be serializable
        by the ProjectEncoder
    attr : str
        Name of the attribute which holds this reference, this name is used by
        setattr during decoding to re-link the de-referenced object.
    ref : Optional
        Object to which the :class:`Reference` refers, must have a 'uid'
        attribute and be serializable by the ProjectEncoder

    Examples
    --------
    >>> class Sensor:
    >>>     def __init__(self, dataset=None):
    >>>         # Note the attr param refers to the parent property
    >>>         # In this case the actual variable self._parent is immaterial
    >>>         self._parent = Reference(self, 'parent', dataset)
    >>>         # A reference can also be instantiated without a referred object
    >>>         self.link = Reference(self, 'link')
    >>>         assert self.link.isnull
    >>>
    >>>     @property
    >>>     def parent(self):
    >>>         return self._parent.dereference()
    >>>
    >>>     @parent.setter
    >>>     def parent(self, value):
    >>>         self._parent.ref = value

    Note that it is currently necessary to define properties as in the above
    example to create the reference when an object is passed, and it is also
    useful to define the getter such that it will return the de-referenced
    object - making the Reference object effectively transparent to any outside
    callers.

    See Also
    --------

    :class:`~dgp.core.models.project.ProjectEncoder`
    :class:`~dgp.core.models.project.ProjectDecoder`

    """
    def __init__(self, owner, attr: str, ref=None):
        self.owner = owner
        self.ref = ref
        self.attr = attr

    @property
    def isnull(self) -> bool:
        """Check if this reference is null (an incomplete reference)

        Returns
        -------
        True
            If any of owner, ref, or attr are None
        False
            If owner, ref, and attr are defined

        """
        return not all([x is not None for x in self.__dict__.values()])

    def dereference(self):
        return self.ref

    def serialize(self):
        """Generate a JSON serializable representation of this Reference for the
        ProjectEncoder.

        Returns
        -------
        None if self.isnull
            else
        Dictionary containing object type, parent, attr, and ref

        """
        if self.isnull:
            return None
        return {
            '_type': self.__class__.__name__,
            'parent': self.owner.uid,
            'attr': self.attr,
            'ref': self.ref.uid
        }
