import functools
import inspect
import json
from datetime import datetime


def type_inference_decorator(func):
    def process_arg(arg):
        try:
            # Try to interpret argument as JSON
            new_arg = json.loads(arg)
        except json.JSONDecodeError:
            try:
                # Try to interpret argument as a float
                new_arg = float(arg)
            except ValueError:
                # If all else fails, assume it's a plain string
                new_arg = arg

        return new_arg

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Attempt to infer the type of the input arguments
        new_args = []
        for arg in args:
            new_arg = process_arg(arg)
            new_args.append(new_arg)

        # Attempt to infer the type of the keyword arguments
        new_kwargs = {}
        for key, value in kwargs.items():
            new_value = process_arg(value)
            new_kwargs[key] = new_value

        # Call the function
        result = func(*new_args, **new_kwargs)

        # Check if result is a dict or list (i.e., JSON-serializable), if so, convert it to a JSON string
        if isinstance(result, (list, dict)):
            return json.dumps(result)
        else:
            return str(result)

    wrapper.__signature__ = inspect.signature(func)

    return wrapper


# Math functions
@type_inference_decorator
def add(a, b):
    return a + b


@type_inference_decorator
def subtract(a, b):
    return a - b


@type_inference_decorator
def multiply(a, b):
    return a * b


@type_inference_decorator
def divide(a, b):
    return a / b


# String functions
@type_inference_decorator
def length(s):
    return len(s)


@type_inference_decorator
def uppercase(s):
    return s.upper()


@type_inference_decorator
def lowercase(s):
    return s.lower()


@type_inference_decorator
def concat(s1, s2):
    return s1 + s2


# Data manipulation
@type_inference_decorator
def append(lst, el):
    lst.append(el)
    return lst


@type_inference_decorator
def remove(lst, el):
    lst.remove(el)
    return lst


@type_inference_decorator
def sort(lst):
    lst.sort()
    return lst


@type_inference_decorator
def now():
    return datetime.now().isoformat()


# Unwrapped functions
def identity(x):
    return x
