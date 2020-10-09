import yaml
import config_field
import config_template
import base_configuration

import test_constants

with open("test_config.yaml", 'r') as yaml_file:
   params = yaml.load(yaml_file, yaml.SafeLoader)

person_template = config_template._Template(
    fields=[
        config_field.Field(name=test_constants.Constants.NUM_ARMS, types=[int], key=test_constants.Constants.NUM_ARMS, requirements=[lambda x: x > 0]),
        config_field.Field(name=test_constants.Constants.NUM_LEGS, types=[int], key=test_constants.Constants.NUM_LEGS, requirements=[lambda x: x > 0])
    ],
    level=[test_constants.Constants.PERSON]
)

cat_template = config_template._Template(
    dependent_variables = [test_constants.Constants.ANIMAL_TYPE],
    dependent_variables_required_values = [[test_constants.Constants.CAT]],
    fields=[
        config_field.Field(name=test_constants.Constants.WHISKERS, types=[bool], key=test_constants.Constants.WHISKERS, requirements=[lambda x: x is True])
    ],
    level=[test_constants.Constants.ANIMAL, test_constants.Constants.CAT]
)

dog_template = config_template._Template(
    dependent_variables = [test_constants.Constants.ANIMAL_TYPE],
    dependent_variables_required_values = [[test_constants.Constants.DOG]],
    fields=[
        config_field.Field(name=test_constants.Constants.WHISKERS, types=[bool], key=test_constants.Constants.WHISKERS, requirements=[lambda x: x is False])
    ],
    level=[test_constants.Constants.ANIMAL, test_constants.Constants.DOG]
)

animal_template = config_template._Template(
    fields=[
        config_field.Field(name=test_constants.Constants.TYPE, types=[str], key=test_constants.Constants.ANIMAL_TYPE, 
        requirements=[lambda x: x in [test_constants.Constants.CAT, test_constants.Constants.DOG]])
    ],
    level=[test_constants.Constants.ANIMAL],
    nested_templates = [cat_template, dog_template]
)

base_config_template = config_template._Template(
    fields=[
        config_field.Field(name=test_constants.Constants.NAME, types=[str], key=test_constants.Constants.NAME),
        config_field.Field(name=test_constants.Constants.SURNAME, types=[str], key=test_constants.Constants.SURNAME),
        config_field.Field(name=test_constants.Constants.TYPE, types=[str], key=test_constants.Constants.TYPE, 
        requirements=[lambda x: x in [test_constants.Constants.PERSON, test_constants.Constants.ANIMAL]])
    ],
    nested_templates=[person_template, animal_template]
)


bc = base_configuration.BaseConfiguration(configuration=params, template=base_config_template)
