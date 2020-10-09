from abc import ABC, abstractmethod

from typing import List, Union, Optional

import config_field


class _Template:

    def __init__(
        self, 
        fields: List[config_field.Field], 
        nested_templates: Optional[List] = None, 
        level: Optional[List[str]] = None, 
        dependent_variables: Optional[List[str]] = None, 
        dependent_variables_required_values: Optional[List[List]] = None
    ):
        self._fields = fields
        self._nested_templates = nested_templates
        self._level = level
        self._dependent_variables = dependent_variables
        self._dependent_variables_required_values = dependent_variables_required_values

    @property
    def fields(self) -> List[config_field.Field]:
        return self._fields

    @property
    def nested_templates(self) -> List:
        return self._nested_templates or []

    @property
    def level(self) -> Union[List[str], None]:
        return self._level

    @property
    def dependent_variables(self) -> Union[List[str], None]:
        return self._dependent_variables

    @property
    def dependent_variables_required_values(self) -> Union[List[List], None]:
        return self._dependent_variables_required_values

    @property
    def template_name(self) -> Union[str, None]:
        if self._level:
            return self._level[-1]
        else:
            return None
