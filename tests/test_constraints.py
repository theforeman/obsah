import argparse

import pytest

from obsah.constraints import validate_constraints


@pytest.mark.parametrize("constraints,args,errors", [
    ([['a', 'b']], {'a': 1, 'b': 1}, []),
    ([['a', 'b']], {'a': 1}, ["['a', 'b'] are required together, missing: ['b']"]),
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
    ([['a', 1, ['b', 'c']]], {'a': 1, 'b': 1, 'c': 1}, ["['b', 'c'] are forbidden because a is 1"]),
])
def test_forbidden_if(constraints, args, errors):
    metadata = {'constraints': {'forbidden_if': constraints}}
    found_errors = validate_constraints(metadata, argparse.Namespace(**args))
    assert errors == found_errors


@pytest.mark.parametrize("constraints,args,errors", [
    ([['database_mode', 'external', [['iop', 'enabled']]]], {'database_mode': 'external', 'iop': 'enabled'},
     ["['iop=enabled'] are forbidden because database_mode is external"]),
    ([['database_mode', 'external', [['iop', 'enabled']]]], {'database_mode': 'external', 'iop': 'disabled'}, []),
    ([['database_mode', 'external', [['iop', 'enabled']]]], {'database_mode': 'internal', 'iop': 'enabled'}, []),
    ([['database_mode', 'external', [['iop', 'enabled']]]], {'database_mode': 'external'}, []),
    ([['mode', 'advanced', [['feature_a', 'on'], ['feature_b', 'high']]]],
     {'mode': 'advanced', 'feature_a': 'on', 'feature_b': 'high'},
     ["['feature_a=on', 'feature_b=high'] are forbidden because mode is advanced"]),
    ([['mode', 'advanced', [['feature_a', 'on'], ['feature_b', 'high']]]],
     {'mode': 'advanced', 'feature_a': 'on', 'feature_b': 'low'},
     ["['feature_a=on'] are forbidden because mode is advanced"]),
    ([['mode', 'advanced', [['feature_a', 'on'], ['feature_b', 'high']]]],
     {'mode': 'advanced', 'feature_a': 'off', 'feature_b': 'high'},
     ["['feature_b=high'] are forbidden because mode is advanced"]),
    ([['mode', 'advanced', [['feature_a', 'on'], ['feature_b', 'high']]]],
     {'mode': 'basic', 'feature_a': 'on', 'feature_b': 'high'}, []),
    ([['a', 1, [['b', 2]]]], {'a': 1, 'b': 3}, []),
    ([['a', 1, [['b', 2]]]], {'a': 2, 'b': 2}, []),
    ([['a', 1, [['b', 2]]]], {'a': 1}, []),
    ([['a', 1, [['b', 2]]], ['c', 3, [['d', 4]]]], {'a': 1, 'b': 2, 'c': 3, 'd': 4},
     ["['b=2'] are forbidden because a is 1", "['d=4'] are forbidden because c is 3"]),
    ([['a', 1, ['b']], ['c', 2, [['d', 3]]]], {'a': 1, 'b': 1, 'c': 2, 'd': 3},
     ["['b'] are forbidden because a is 1", "['d=3'] are forbidden because c is 2"]),
    ([['a', 1, ['b', ['c', 2]]]], {'a': 1, 'b': 1, 'c': 2},
     ["['b', 'c=2'] are forbidden because a is 1"]),
])
def test_forbidden_if_enhanced(constraints, args, errors):
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
