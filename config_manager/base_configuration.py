import collections
import inspect
import os
import warnings
from typing import Any
from typing import Dict
from typing import List
from typing import Union
from typing import overload
from typing import Optional
from typing import Tuple
from typing import Callable

import os
import abc
from typing import Any
from typing import Dict

import yaml

import config_template
import config_field


class BaseConfiguration(abc.ABC):
    """Object in which to store configuration parameters."""
    def __init__(self, configuration: Dict, template: config_template._Template) -> None: #TODO: make union with posix path object
        """
        Initialise.

        Args:
            configuration: 
            template: 
        """
        self._configuration = configuration
        self._template = template

        self._attribute_name_key_map: Dict[str, Union[List[str], str]] = {}
        self._attribute_name_types_map: Dict[str, List] = {}
        self._attribute_name_requirements_map: Dict[str, List[Callable]] = {}
        
        self._check_and_set_template(self._template)

        # self._get_induced_configuration_parameters()
        # self._verify_configuration()

    def _validate_field(self, field: config_field.Field, data: Dict, level: str) -> None:
        """
        TODO
        """
        # ensure field exists
        assert field.name in data, f"{field.name} not specified in configuration at level {level}"
        
        self._validate_field_type(data[field.name], field.name, field.types, level=level)
        self._validate_field_requirements(data[field.name], field.name, field.requirements, level=level)

        print(f"Field '{field.name}' at level '{level}' in config validated.")

    def _validate_field_type(self, field_value: Any, field_name: str, permitted_types: List, level: Optional[str]) -> None:
        """
        Ensure value give for field is correct type.

        Args:
            field_value:
            field_name: 
            permitted_types:
            level:

        Raises:
            AssertionError 
        """
        type_assertion_error_message = f"Level: '{level}': " or ""
        type_assertion_error_message = (
                f"{type_assertion_error_message}"
                f"Type of value given for field {field_name} is {type(field_value)}."
                f"Must be one of {permitted_types}.")
        assert isinstance(field_value, permitted_types), type_assertion_error_message

    def _validate_field_requirements(self, field_value: Any, field_name: str, field_requirements: List[Callable], level: Optional[str]):
        """
        Ensure requirements are satisfied for field value.

        Args:
            field_value:
            field_name:
            field_requirements:
            level:

        Raises:
            AssertionError
        """
        base_error = f"Level: '{level}': " or ""
        if field_requirements:
            for r, requirement in enumerate(field_requirements):
                requirement_assertion_error_message = f"{base_error}Additional requirement check {r} for field {field_name} failed."
                assert requirement(field_value), requirement_assertion_error_message
    
    def _template_is_needed(self, template: config_template._Template):
        return all(
                getattr(self, dependent_variable) in dependent_variable_required_values 
                for dependent_variable, dependent_variable_required_values in 
                zip(template.dependent_variables, template.dependent_variables_required_values)
            )

    def _check_and_set_template(self, template: config_template._Template):
        data = self._configuration
        if template.level:
            level_name = '/'.join(template.level)
            for level in template.level:
                data = data.get(level)
        else:
            level_name = "ROOT"

        # only check template if required
        if not template.dependent_variables or self._template_is_needed(template=template):

            fields_to_check = list(data.keys())

            for field in template.fields:
                self._validate_field(field=field, data=data, level=level_name)
                self._set_property(property_name=field.key, property_value=data[field.name])
                self._set_attribute_name_key_map(property_name=field.key, configuration_key_chain=template.level)
                self._set_attribute_name_types_map(property_name=field.key, types=field.types)
                self._set_attribute_name_requirements_map(property_name=field.key, requirements=field.requirements)
                print(f"Field '{field.name}' at level '{level_name}' in config set with key '{field.key}'.")
                fields_to_check.remove(field.name)
            for nested_template in template.nested_templates:
                self._check_and_set_template(nested_template)
                fields_to_check.remove(nested_template.template_name)

            fields_unchecked_assertion_error = \
                f"There are fields at level '{level_name}' of config that have not been validated: {fields_to_check}"
            assert not fields_to_check, fields_unchecked_assertion_error

    # @abc.abstractmethod
    # def _get_induced_configuration_parameters(self):
    #     """Read in configuration variables and make relevant params properties of class."""
    #     pass

    # @abc.abstractmethod
    # def _verify_configuration(self):
    #     """Implements logic to establish valid configuration specification."""
    #     pass

    @property
    def config(self) -> Dict:
        return self._configuration

    def save_configuration(self, path: str) -> None:
        """
        Save copy of configuration to specified path. 

        Args:
            path:: path to folder in which to save configuration
        """
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "config.yaml"), "w") as f:
            yaml.dump(self._configuration, f)

    def get_property(self, property_name: str) -> Any:
        """
        Get property of class from property name.

        Args:
            property_name: name of class property
        
        Returns:
            property_value: value associated with class property.

        Raises:
            AttributeError: if attribute is missing from configuration class.
        """
        property_value = getattr(self, property_name)
        return property_value

    def _set_property(self, property_name: str, property_value: Any) -> None:
        """
        Make property_name an attribute of this configuration class with value property_value.

        Args:
            property_name: name of attribute created for class.
            property_value: corresponding value for property.
            configuration_key_chain: chain of keys in original configuration dictionary from which property_value is obtained.
            (to be used if and only if method is called in initial construction).
        """
        if hasattr(self, property_name):
            existing_property_value = getattr(self, property_name)
            raise AssertionError(
                f"Illegally attempting to overwrite property {property_name}"
                f" from {existing_property_value} to {property_value}."
                )
        setattr(self, property_name, property_value)

    def _set_attribute_name_types_map(self, property_name: str, types: List) -> None:
        """
        """
        self._attribute_name_types_map[property_name] = types

    def _set_attribute_name_requirements_map(self, property_name: str, requirements: List[Callable]) -> None:
        """
        """
        self._attribute_name_requirements_map[property_name] = requirements

    def _set_attribute_name_key_map(self, property_name: str, configuration_key_chain: List[str]) -> None:
        """
        Store in separate map (property_name, configuration_key_chain) so that configuration dictionary can 
        be modified along with class property if amend_property method is called at later time.

        Args:
            property_name: name of attribute created for class.
            configuration_key_chain: chain of keys in original configuration dictionary from which property_value is obtained.
            (to be used if and only if method is called in initial construction).
        """
        self._attribute_name_key_map[property_name] = configuration_key_chain

    def add_property(self, property_name: str, property_value: Any) -> None:
        """
        Make property_name an attribute of this configuration class with value property_value.
        Also add with key value pair (property_name, property_value) to configuration dictionary of class.

        Args:
            property_name: name of attribute created for class (also key to store property in configuration dictionary).
            property_value: corresponding value for property.
        """
        self._set_property(property_name=property_name, property_value=property_value)
        self._configuration[property_name] = property_value

    def amend_property(self, property_name: str, new_property_value: Any) -> None:
        """
        Change property in class. 
        Also modify dictionary entry in configuration object (self._configuration).

        Args:
            property_name: name of attribute created for class.
            property_value: corresponding (new) value for property.
        """
        assert hasattr(self, property_name), f"Property name '{property_name}' not yet configured. Cannot amend."

        # get relevant information associated with original field
        configuration_key_chain = self._attribute_name_key_map[property_name]
        permitted_types = self._attribute_name_types_map[property_name]
        field_requirements = self._attribute_name_requirements_map[property_name]

        # check new property value is valid
        self._validate_field_type(field_value=new_property_value, field_name=property_name, permitted_types=permitted_types)
        self._validate_field_requirements(field_value=new_property_value, field_name=property_name, field_requirements=field_requirements) 

        self._configuration[property_name] = new_property_value
        setattr(self, property_name, new_property_value)
        self._maybe_reconfigure(property_name)

    # @abc.abstractmethod
    # def _maybe_reconfigure(self, property_name: str) -> None:
    #     """
    #     Enact changes to config based on change to property_name.

    #     Args:
    #         property_name: name of field to check
    #     """
    #     pass
