"""
obsah constraints module

implements validation for constraints used in obsah CLIs
"""
import argparse
import collections.abc


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
            missing_args = [arg for arg in constraint if arg not in args]
            errors.append(
                f"{[variable_to_parameter(x) for x in constraint]} are required together, missing: {[variable_to_parameter(x) for x in missing_args]}"
            )

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

    def _validate_forbidden_if_constraint(constraint):
        trigger_arg, trigger_value, forbidden_items = constraint
        if trigger_arg not in args or getattr(args, trigger_arg) != trigger_value:
            return []

        violated = []
        for item in forbidden_items:
            if isinstance(item, str):
                if item in args:
                    violated.append(variable_to_parameter(item))
            elif isinstance(item, collections.abc.Collection) and len(item) == 2:
                arg, val = item
                if arg in args and getattr(args, arg) == val:
                    violated.append(f"{variable_to_parameter(arg)}={val}")

        if violated:
            return [f"{violated} are forbidden because {variable_to_parameter(trigger_arg)} is {trigger_value}"]

        return []

    for constraint in constraints.get('forbidden_if', []):
        errors.extend(_validate_forbidden_if_constraint(constraint))

    for constraint in constraints.get('mutually_exclusive', []):
        present_args = [True for arg in constraint if arg in args]
        if len(present_args) > 1:
            errors.append(f"{constraint} are mutually exclusive")

    return errors
