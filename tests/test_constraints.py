import argparse

import pytest

from obsah.constraints import validate_constraints


@pytest.mark.parametrize("constraints,args,errors", [
    ([['a', 'b']], {'a': 1, 'b': 1}, []),
    ([['a', 'b']], {'a': 1}, ["['a', 'b'] are required together"]),
    ([['a', 'b']], {}, []),
])
def test_required_together(constraints, args, errors):
    metadata = {'constraints': {'required_together': constraints}}
    found_errors = validate_constraints(metadata, argparse.Namespace(**args))
    assert errors == found_errors


@pytest.mark.parametrize("constraints,args,errors", [
    ([['a', 'b']], {'a': 1, 'b': 1}, []),
    ([['a', 'b']], {'a': 1}, []),
    ([['a', 'b']], {}, ["one of ['a', 'b'] is required"]),
])
def test_required_one_of(constraints, args, errors):
    metadata = {'constraints': {'required_one_of': constraints}}
    found_errors = validate_constraints(metadata, argparse.Namespace(**args))
    assert errors == found_errors


@pytest.mark.parametrize("constraints,args,errors", [
    ([['a', 1, ['b']]], {'a': 1, 'b': 1}, []),
    ([['a', 1, ['b']]], {'a': 1}, ["['b'] are required because a is 1"]),
    ([['a', 1, ['b']]], {'a': 2}, []),
])
def test_required_if(constraints, args, errors):
    metadata = {'constraints': {'required_if': constraints}}
    found_errors = validate_constraints(metadata, argparse.Namespace(**args))
    assert errors == found_errors


@pytest.mark.parametrize("constraints,args,errors", [
    ([['a', 1, ['b']]], {'a': 1, 'b': 1}, ["['b'] are forbidden because a is 1"]),
    ([['a', 1, ['b']]], {'a': 1}, []),
    ([['a', 1, ['b']]], {'a': 2, 'b': 1}, []),
])
def test_forbidden_if(constraints, args, errors):
    metadata = {'constraints': {'forbidden_if': constraints}}
    found_errors = validate_constraints(metadata, argparse.Namespace(**args))
    assert errors == found_errors


@pytest.mark.parametrize("constraints,args,errors", [
    ([['a', 'b']], {'a': 1, 'b': 1}, ["['a', 'b'] are mutually exclusive"]),
    ([['a', 'b']], {'a': 1}, []),
    ([['a', 'b']], {}, []),
])
def test_mutually_exclusive(constraints, args, errors):
    metadata = {'constraints': {'mutually_exclusive': constraints}}
    found_errors = validate_constraints(metadata, argparse.Namespace(**args))
    assert errors == found_errors
