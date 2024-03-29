import abc
import collections
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import yaml

from config_manager import config_field, config_template


class BaseConfiguration(abc.ABC):
    """Object in which to store configuration parameters.

    Makes checks on configuration provided
    (type, other requirements specified by templates etc.)
    """

    def __init__(
        self,
        configuration: Union[Dict, str],
        template: config_template.Template,
        changes: List[Dict] = [],
        verbose: bool = True,
    ) -> None:
        """
        Initialise.

        Args:
            configuration: either a (possibly nested) dictionary of configuration
            parameters or a path to a .yaml file containing the configuration.
            template: template object specifying requirements and type checks
            configuration needs to adhere to.
            verbosity: whether or not to print statements on progress of
            configuration parsing.

        Raises:
            FileNotFoundError: if configuration is given as path and cannot be found.
            ValueError: if configuration is not of type dictionary or str.
        """
        if isinstance(configuration, str):
            self._configuration = self._read_config_from_path(configuration)
        elif isinstance(configuration, dict):
            self._configuration = configuration
        else:
            raise ValueError(
                "object passed to 'configuration' parameter is "
                f"type {type(configuration)}. Should be dictionary or path (str)."
            )

        # perform any specified changes
        for change in changes:
            self._configuration = self._update_config(
                configuration_dictionary=self._configuration, update_dictionary=change
            )

        self._template = template

        self._attribute_name_key_map: Dict[str, Union[List[str], str]] = {}
        self._attribute_name_types_map: Dict[str, List] = {}
        self._attribute_name_requirements_map: Dict[str, List[Callable]] = {}

        self._check_and_set_template(self._template)

    def _update_config(
        self, configuration_dictionary: Dict, update_dictionary: Dict
    ) -> Dict:
        for k, v in update_dictionary.items():
            if isinstance(v, collections.abc.Mapping):
                configuration_dictionary[k] = self._update_config(
                    configuration_dictionary.get(k, {}), v
                )
            else:
                configuration_dictionary[k] = v
        return configuration_dictionary

    def _read_config_from_path(self, path: str) -> Dict:
        """Read configuration from yaml file path.

        Args:
            path: path to .yaml file.

        Returns:
            configuration: configuration in dictionary format.

        Raises:
            FileNotFoundError if file cannot be found at path specified.
        """
        try:
            with open(path, "r") as yaml_file:
                configuration = yaml.load(yaml_file, yaml.SafeLoader)
        except FileNotFoundError:
            raise FileNotFoundError("Yaml file could not be read.")

        return configuration

    @staticmethod
    def validate_field(field: config_field.Field, data: Dict, level: str) -> None:
        """
        Orchestrates checks on data provided for particular field in config.

        Args:
            field: specifies requirements for field.
            data: user provided configuration data.
            level: description of nesting in configuration.

        Raises:
            AssertionError: if field does not exist.
            AssertionError: if data is of incorrect type.
            AssertionError: if data does not meet requirements specified by
            field object.
        """
        # ensure field exists
        assert (
            field.name in data
        ), f"{field.name} not specified in configuration at level {level}"

        BaseConfiguration.validate_field_type(
            data[field.name], field.name, field.types, level=level
        )
        BaseConfiguration.validate_field_requirements(
            data[field.name], field.name, field.requirements, level=level
        )

        print(f"Field '{field.name}' at level '{level}' in config validated.")

    @staticmethod
    def validate_field_type(
        field_value: Any,
        field_name: str,
        permitted_types: List,
        level: Optional[str] = "",
    ) -> None:
        """
        Ensure value give for field is correct type.

        Args:
            field_value: data provided for particular field in config.
            field_name: name of field.
            permitted_types: list of allowed types according to field object.
            level: description of nesting in configuration.

        Raises:
            AssertionError: if data is of incorrect type.
        """
        type_assertion_error_message = f"Level: '{level}': " or ""
        type_assertion_error_message = (
            f"{type_assertion_error_message}"
            f"Type of value given for field {field_name} is {type(field_value)}."
            f"Must be one of {permitted_types}."
        )
        assert isinstance(field_value, permitted_types), type_assertion_error_message

    @staticmethod
    def validate_field_requirements(
        field_value: Any,
        field_name: str,
        field_requirements: List[Callable],
        level: Optional[str] = "",
    ):
        """
        Ensure requirements are satisfied for field value.

        Args:
            field_value: data provided for particular field in config.
            field_name: name of field.
            field_requirements: list of lambda functions that describe
            requirements for field_value.
            level: description of nesting in configuration.

        Raises:
            AssertionError: if data does not meet requirements specified by
            field object.
        """
        base_error = f"Level: '{level}': " or ""
        if field_requirements:
            for r, requirement in enumerate(field_requirements):
                requirement_assertion_error_message = (
                    f"{base_error}Additional requirement check {r} "
                    f"for field {field_name} failed."
                )
                assert requirement(field_value), requirement_assertion_error_message

    def _template_is_needed(self, template: config_template.Template) -> bool:
        """
        Checks whether according to specified conditions, the template
        needs to be checked. For example, some fields are only relevant if
        another field higher up in the configuration tree are set to a particular value.

        Args:
            template: object specifying required config structure.

        Returns:
            is_needed: whether or not template needs to be checked.
        """
        reduced_dependent_variables = []
        for dependent_variable in template.dependent_variables:
            if isinstance(dependent_variable, list):
                reduced_dependent_variables.append(
                    dependent_variable[template.check_count]
                )
            elif isinstance(dependent_variable, str):
                reduced_dependent_variables.append(dependent_variable)
            else:
                raise ValueError("dependent_variable must be list of str or str.")

        return all(
            getattr(self, dependent_variable) in dependent_variable_required_values
            for dependent_variable, dependent_variable_required_values in zip(
                reduced_dependent_variables,
                template.dependent_variables_required_values,
            )
        )

    def _check_and_set_template(
        self, template: config_template.Template, check: Optional[List[str]] = []
    ) -> None:
        """
        Checks whether data provided is consistent with template.
        Also performs assignment of relevant configuration parameters as
        attributes of class.

        This method is or can be called recursively depending on structure of template.

        Args:
            template: object specifying requirements for configuration.

        Raises:
            AssertionError: If there are fields of configuration that are not
            covered by template and have not been checked as a result.
        """
        data = self._configuration

        key_prefixes = []

        if template.level:
            reduced_template_level = []

            for sub_level in template.level:
                if isinstance(sub_level, dict):
                    sub_level_keys = list(sub_level.keys())
                    key_prefix = sub_level_keys[
                        template.check_count
                    ]  # current_sub_level
                    reduced_template_level.append(sub_level[key_prefix])
                    key_prefixes.append(key_prefix)
                elif isinstance(sub_level, str):
                    reduced_template_level.append(sub_level)
                else:
                    raise ValueError(
                        "each sub level of template level must be list of str or str"
                    )

            level_name = "/".join(reduced_template_level)
            for level in reduced_template_level:
                data = data.get(level)
        else:
            level_name = "ROOT"

        # only check template if required
        if template.dependent_variables:
            if not self._template_is_needed(template=template):
                check.remove(template.template_name)
        if (
            not template.dependent_variables
            or template.template_name in check
        ):

            fields_to_check = list(data.keys())

            for field in template.fields:
                self.validate_field(field=field, data=data, level=level_name)

                if template.key_prefix is not None:
                    field_key = f"{template.key_prefix}_{field.key}"
                else:
                    field_key = field.key
                    for key_prefix in key_prefixes:
                        field_key = f"{key_prefix}_{field_key}"

                self._set_property(
                    property_name=field_key, property_value=data[field.name]
                )
                self._set_attribute_name_key_map(
                    property_name=field_key, configuration_key_chain=template.level
                )
                self._set_attribute_name_types_map(
                    property_name=field_key, types=field.types
                )
                self._set_attribute_name_requirements_map(
                    property_name=field_key, requirements=field.requirements
                )
                fields_to_check.remove(field.name)
            for nested_template in template.nested_templates:
                self._check_and_set_template(nested_template, check=fields_to_check)
                if nested_template.check_count:
                    if nested_template.template_name in fields_to_check:
                        fields_to_check.remove(nested_template.template_name)

            fields_unchecked_assertion_error = (
                f"There are fields at level '{level_name}' of config "
                f"that have not been validated: {fields_to_check}"
            )
            assert not fields_to_check, fields_unchecked_assertion_error

            template.register_check()

    @property
    def config(self) -> Dict:
        return self._configuration

    def save_configuration(
        self, folder_path: str, file_name: str = "config.yaml"
    ) -> None:
        """
        Save copy of configuration to specified path.

        Args:
            folder_path: path to folder in which to save configuration
            file_name: name of file to save configuration under.
        """
        os.makedirs(folder_path, exist_ok=True)
        with open(os.path.join(folder_path, file_name), "w") as f:
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
        Make property_name an attribute of this configuration class with
        value property_value.

        Args:
            property_name: name of attribute created for class.
            property_value: corresponding value for property.
            configuration_key_chain: chain of keys in original configuration
            dictionary from which property_value is obtained.
            (to be used if and only if method is called in initial construction).
        """
        if hasattr(self, property_name):
            existing_property_value = getattr(self, property_name)
            raise AssertionError(
                f"Illegally attempting to overwrite property {property_name}"
                f" from {existing_property_value} to {property_value}."
            )
        setattr(self, property_name, property_value)

    def _set_attribute_name_types_map(self, property_name: str, types: Tuple) -> None:
        """
        Store in separate map (property_name, types) so that if/when amendments
        are made, type checks can still be performed on new value.

        Args:
            property_name: name of attribute created for class.
            types: set of valid types for field associated with property_name
        """
        self._attribute_name_types_map[property_name] = types

    def _set_attribute_name_requirements_map(
        self, property_name: str, requirements: List[Callable]
    ) -> None:
        """
        Store in separate map (property_name, requirements) so that if/when amendments
        are made, requirements checks can still be performed on new value.

        Args:
            property_name: name of attribute created for class.
            requirements: list of lambda functions that specify requirements
            for field associated with property_name.
        """
        self._attribute_name_requirements_map[property_name] = requirements

    def _set_attribute_name_key_map(
        self, property_name: str, configuration_key_chain: List[str]
    ) -> None:
        """
        Store in separate map (property_name, configuration_key_chain) so that
        configuration dictionary can be modified along with class property
        if amend_property method is called at later time.

        Args:
            property_name: name of attribute created for class.
            configuration_key_chain: chain of keys in original configuration dictionary
            from which property_value is obtained. (to be used if and only if
            method is called in initial construction).
        """
        self._attribute_name_key_map[property_name] = configuration_key_chain

    def add_property(self, property_name: str, property_value: Any) -> None:
        """
        Make property_name an attribute of this configuration class with
        value property_value.
        Also add with key value pair (property_name, property_value)
        to configuration dictionary of class.

        Args:
            property_name: name of attribute created for class (also key to store
            property in configuration dictionary).
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
        assert hasattr(
            self, property_name
        ), f"Property name '{property_name}' not yet configured. Cannot amend."

        # get relevant information associated with original field
        configuration_key_chain = self._attribute_name_key_map[property_name]
        permitted_types = self._attribute_name_types_map[property_name]
        field_requirements = self._attribute_name_requirements_map[property_name]

        # check new property value is valid
        self.validate_field_type(
            field_value=new_property_value,
            field_name=property_name,
            permitted_types=permitted_types,
        )
        self.validate_field_requirements(
            field_value=new_property_value,
            field_name=property_name,
            field_requirements=field_requirements,
        )

        self._configuration[property_name] = new_property_value
        setattr(self, property_name, new_property_value)
        # TODO: self._maybe_reconfigure(property_name)
