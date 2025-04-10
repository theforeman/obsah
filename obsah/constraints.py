"""
obsah constraints module

implements validation for constraints used in obsah CLIs
"""
import argparse

def validate_constraints(metadata: dict, args: argparse.Namespace):
    """
    validate arguments passed in on the CLI against constraints from a playbook
    """
    constraints: dict = metadata.get('constraints', {})
    variables: list = metadata.get('variables', [])

    def variable_to_parameter(name):
        for variable in variables:
            if variable.name == name:
                return variable.parameter
        return name

    errors = []
    for constraint in constraints.get('required_together', []):
        present_args = [arg in args for arg in constraint]
        if not all(present_args) and any(present_args):
            errors.append(f"{[variable_to_parameter(x) for x in constraint]} are required together")
    for constraint in constraints.get('required_one_of', []):
        present_args = [arg in args for arg in constraint]
        if not any(present_args):
            errors.append(f"one of {[variable_to_parameter(x) for x in constraint]} is required")
    for constraint in constraints.get('required_if', []):
        argument_name, argument_value, required_arguments = constraint
        if argument_name in args and getattr(args, argument_name) == argument_value:
            if not all(arg in args for arg in required_arguments):
                required = [variable_to_parameter(x) for x in required_arguments]
                errors.append(f"{required} are required because {variable_to_parameter(argument_name)} is {argument_value}")
    for constraint in constraints.get('forbidden_if', []):
        argument_name, argument_value, forbidden_arguments = constraint
        if argument_name in args and getattr(args, argument_name) == argument_value:
            if any(arg in args for arg in forbidden_arguments):
                forbidden = [variable_to_parameter(x) for x in forbidden_arguments]
                errors.append(f"{forbidden} are forbidden because {variable_to_parameter(argument_name)} is {argument_value}")
    for constraint in constraints.get('mutually_exclusive', []):
        present_args = [True for arg in constraint if arg in args]
        if len(present_args) > 1:
            errors.append(f"{constraint} are mutually exclusive")
    return errors
