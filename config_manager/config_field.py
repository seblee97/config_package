from typing import List, Optional, Tuple, Union


class Field:

    def __init__(self, name: str, key: str, types: List, requirements: Optional[List] = None):
        """
        Class constructor.

        Args:
            name: leaf-level name given to parameter/property in configuration file.
            key: name (ideally defined in a constants file) under which parameter 
            is stored in configuration object and subsequently retrieved with.
            types: list of valid types for property.
            requirements: list of lambda functions to test validity of property.
        """
        self._name = name
        self._key = key
        self._types: Tuple = tuple(types)
        self._requirements = requirements

    @property
    def name(self) -> str:
        return self._name

    @property
    def key(self) -> str:
        return self._key

    @property
    def types(self) -> List:
        return self._types

    @property
    def requirements(self) -> Union[List, None]:
        return self._requirements