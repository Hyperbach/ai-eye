import datetime
import json
import functools
from datetime import datetime


def exception_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            value = func(*args, **kwargs)
            return output_wrapper(value=value)
        except Exception as e:
            return output_wrapper(error=str(e))

    return wrapper


# Wrapper function
def output_wrapper(value=None, error=None):
    output = {}
    if value is not None:
        output['result'] = value
    if error is not None:
        output['error'] = error
    return json.dumps(output)


# Math functions
@exception_handler
def add(a, b):
    a = float(a)
    b = float(b)
    return a + b


@exception_handler
def subtract(a, b):
    a = float(a)
    b = float(b)
    return a - b


@exception_handler
def multiply(a, b):
    a = float(a)
    b = float(b)
    return a * b


@exception_handler
def divide(a, b):
    a = float(a)
    b = float(b)
    if b != 0:
        return a / b
    else:
        raise ValueError("Division by zero")


# String functions
@exception_handler
def length(s):
    return len(s)


@exception_handler
def uppercase(s):
    return s.upper()


@exception_handler
def lowercase(s):
    return s.lower()


@exception_handler
def concat(s1, s2):
    return s1 + s2


# Data manipulation
@exception_handler
def append(lst, el):
    lst = json.loads(lst)
    el = json.loads(el)
    lst.append(el)
    return lst


@exception_handler
def remove(lst, el):
    lst = json.loads(lst)
    el = json.loads(el)
    if el in lst:
        lst.remove(el)
    return lst


@exception_handler
def sort(lst):
    lst = json.loads(lst)
    lst.sort()
    return lst


@exception_handler
def now():
    return datetime.now().isoformat()


# Unwrapped functions
def identity(x):
    return x
