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

# class Parameters(object):

#     def __init__(self, parameters: Dict[str, Any]):
#         self._config = parameters

#     @overload
#     def get(self, property_name: str):
#         ...

#     @overload
#     def get(self, property_name: List[str]):
#         ...

#     def get(self, property_name):
#         """
#         Return value associated with property_name in configuration

#         :param property_name: name of parameter in configuration.
#                               Could be list if accessing nested part of dict.
#         :return: value associated with property_name
#         """
#         if isinstance(property_name, list):
#             value = self._config
#             for prop in property_name:
#                 value = value.get(prop, "Unknown Key")
#                 if value == "Unknown Key":
#                     raise ValueError("Config key {} unrecognised".format(prop))
#             return value
#         elif isinstance(property_name, str):
#             value = self._config.get(property_name, "Unknown Key")
#             if value == "Unknown Key":
#                 raise ValueError("Config key {} unrecognised".format(property_name))
#             else:
#                 return value
#         else:
#             raise TypeError("property_name supplied has wrong type. \
#                     Must be list of strings or string.")

#     def get_property_description(self, property_name: str) -> str:
#         """
#         Return description of configuration property

#         :param property_name: name of parameter to query for description
#         :return: description of property in configuration
#         """
#         # TODO: Is this worth doing? .yaml not particularly amenable
#         raise NotImplementedError

#     def _validate_field(self, field: Field, data: Dict, level: str) -> None:
#         field_name = field.get_name()
#         allowed_field_types = field.get_types()
#         additional_reqs = field.get_reqs()

#         # ensure field exists
#         assert field_name in data, \
#             "{} not specified in configuration at level {}".format(
#                 field_name, level
#                 )

#         # ensure value give for field is correct type
#         field_value = data[field_name]
#         assert isinstance(field_value, allowed_field_types), \
#             "Type given for field {} at level {} in config is {}. \
#                 Must be one of {}"                                  .format(
#                     field_name, level, type(field_value), allowed_field_types
#                     )

#         # ensure other requirements are satisfied
#         if additional_reqs:
#             for r, requirement in enumerate(additional_reqs):
#                 assert requirement(field_value), \
#                     "Additional requirement check {} for field {} \
#                         failed"                               .format(r, field_name)

#         print("Validating field: {} at level {} in config...".format(field_name, level))

#     def check_template(self, template: _Template):
#         template_attributes = template.get_fields()

#         template_nesting = template.get_levels()
#         data: Union[Dict[str, Any], Any] = self._config
#         if template_nesting == "ROOT":
#             level_name = "ROOT"
#         else:
#             level_name = '/'.join(template_nesting)
#             for level in template_nesting:
#                 data = data.get(level)

#         fields_to_check = list(data.keys())
#         optional_fields = template.get_optional_fields()

#         for template_attribute in template_attributes:
#             if (inspect.isclass(template_attribute) and issubclass(template_attribute, _Template)):
#                 self.check_template(template_attribute)
#                 fields_to_check.remove(template_attribute.get_template_name())
#             else:
#                 self._validate_field(field=template_attribute, data=data, level=level_name)
#                 fields_to_check.remove(template_attribute.get_name())

#         for optional_field in optional_fields:
#             if optional_field in fields_to_check:
#                 fields_to_check.remove(optional_field)
#                 warnings.warn("Optional field {} provided but NOT checked".format(optional_field))

#         assert not fields_to_check, \
#             "There are fields at level {} of config that have not \
#                 been validated: {}"                                   .format(
#                     level_name, ", ".join(fields_to_check)
#                     )

#     def set_property(self,
#                      property_name: Union[str, List[str]],
#                      property_value: Any,
#                      property_description: str = None) -> None:
#         """
#         Add to the configuration specification

#         :param property_name: name of parameter to append to configuration
#         :param property_value: value to set for property in configuration
#         :param property_description (optional): description of property to add
#         to configuration
#         """
#         if property_name in self._config:
#             raise Exception("This field is already defined in the configuration. \
#                 Use ammend_property method to override current entry")
#         else:
#             if isinstance(property_name, str):
#                 self._config[property_name] = property_value
#             else:
#                 raise TypeError("Property name type {} not assignable".format(type(property_name)))

#     def ammend_property(self,
#                         property_name: str,
#                         property_value: Any,
#                         property_description: str = None) -> None:
#         """
#         Add to the configuration specification

#         :param property_name: name of parameter to ammend in configuration
#         :param property_value: value to ammend for property in configuration
#         :param property_description (optional): description of property to add
#         to configuration
#         """
#         raise NotImplementedError
#         if property_name not in self._config:
#             raise Exception("This field is not defined in the configuration. \
#                     Use set_property method to add this entry")
#         else:
#             self._config[property_name] = property_value

#     def show_all_parameters(self) -> None:
#         """
#         Prints entire configuration
#         """
#         print(self._config)

#     def save_configuration(self, save_path: str) -> None:
#         """
#         Saves copy of configuration to specified path. Particularly useful
#         for keeping track of different experiment runs

#         :param save_path: path to folder in which to save configuration
#         """
#         os.makedirs(save_path, exist_ok=True)
#         with open(os.path.join(save_path, "config.yaml"), "w") as f:
#             yaml.dump(self._config, f)

#     def update(self, specific_params: Dict) -> None:
#         """
#         Update parameter entries based on entried in specific_params.

#         specific_params could be nested dictionary
#         """

#         def update_dict(original_dictionary, update_dictionary):
#             for key, value in six.iteritems(update_dictionary):
#                 sub_dict = original_dictionary.get(key, {})
#                 if not isinstance(sub_dict, collections.Mapping):
#                     # no more nesting
#                     original_dictionary[key] = value
#                 elif isinstance(value, collections.Mapping):
#                     # more nesting, recurse
#                     original_dictionary[key] = update_dict(sub_dict, value)
#                 else:
#                     original_dictionary[key] = value

#             return original_dictionary

#         self._config = update_dict(self._config, specific_params)


# # class Configuration(ABC):
# #     """Object in which to store configuration parameters."""

# #     def __init__(self, configuration: Dict):
# #         """
# #         Initialise.

# #         Assign all relevant parameters as attributes of class.
# #         """

# #         self._configuration = configuration

# #         self._get_configuration_parameters()
# #         self._verify_configuration()

# #     @abstractmethod
# #     def _get_configuration_parameters(self):
# #         """Read in configuration variables and make relevant params properties of class."""
# #         raise NotImplementedError("Base class method.")

# #     @abstractmethod
# #     def _verify_configuration(self):
# #         """Implements logic to establish valid configuration specification."""
# #         raise NotImplementedError("Base class method.")

# #     @property
# #     def config(self) -> Dict:
# #         return self._configuration

# #     def save_configuration(self, path: str) -> None:
# #         """
# #         Save copy of configuration to specified path. 

# #         Args:
# #             path:: path to folder in which to save configuration
# #         """
# #         os.makedirs(path, exist_ok=True)
# #         with open(os.path.join(path, "config.yaml"), "w") as f:
# #             yaml.dump(self._configuration, f)

# #     def get_property(self, property_name: str) -> Any:
# #         """
# #         Get property of class from property name.

# #         Args:
# #             property_name: name of class property
        
# #         Returns:
# #             property_value: value associated with class property.

# #         Raises:
# #             AttributeError: if attribute is missing from configuration class.
# #         """
# #         property_value = getattr(self, property_name)
# #         return property_value

# #     def set_property(self, property_name: str, property_value: Any) -> None:
# #         """
# #         Add property to dictionary of configuration variables.
# #         Note this does not (necessarily) add these as properties of the class.

# #         Args:
# #             property_name: key to store property in configuration dictionary.
# #             property_value: corresponding value for property to save.
# #         """
# #         self._configuration[property_name] = property_value
# #         setattr(self, property_name, property_value)
# #         self._maybe_reconfigure(property_name)

# #     @abstractmethod
# #     def _maybe_reconfigure(self, property_name: str) -> None:
# #         """
# #         Enact changes to config based on change to property_name.

# #         Args:
# #             property_name: name of field to check
# #         """
# #         pass
