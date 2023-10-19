import functools
import inspect
import json
import os
from datetime import datetime

from embedchain import App


def type_inference_decorator(needs_context=False):
    """
    A decorator that attempts to infer the type of input arguments and keyword arguments
    passed to the decorated function. It tries to interpret each argument as JSON, then as a float,
    and finally as a plain string, in that order.

    The decorator also checks if the result of the decorated function is a list or dictionary.
    If it is, the result is converted to a JSON string; otherwise, it's converted to a plain string.

    If the `needs_context` parameter is set to True, the decorated function can access an additional
    `context` attribute. For example, the `query_embedchain` function uses this to retrieve the "OPENAI_API_KEY".

    Parameters:
    - needs_context (bool): If set to True, the decorated function can access an additional `context`
                            attribute. Default is False.

    Returns:
    - function: The wrapped function with type inference capabilities.

    Usage:
    @type_inference_decorator()
    def some_function(arg1, arg2):
        ...

    @type_inference_decorator(needs_context=True)
    def another_function(arg1, arg2):
        api_key = get_context()["openaikey"]
        ...
    """

    def decorator(func):

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
        wrapper.needs_context = needs_context

        return wrapper

    return decorator


# Math functions
@type_inference_decorator()
def add(a, b):
    return a + b


@type_inference_decorator()
def subtract(a, b):
    return a - b


@type_inference_decorator()
def multiply(a, b):
    return a * b


@type_inference_decorator()
def divide(a, b):
    return a / b


# String functions
@type_inference_decorator()
def length(s):
    return len(s)


@type_inference_decorator()
def uppercase(s):
    return s.upper()


@type_inference_decorator()
def lowercase(s):
    return s.lower()


@type_inference_decorator()
def concat(s1, s2):
    return s1 + s2


# Data manipulation
@type_inference_decorator()
def append(lst, el):
    lst.append(el)
    return lst


@type_inference_decorator()
def remove(lst, el):
    lst.remove(el)
    return lst


@type_inference_decorator()
def sort(lst):
    lst.sort()
    return lst


@type_inference_decorator()
def now():
    return datetime.now().isoformat()


def get_context():
    """
    Dynamically retrieves the context of the calling function if it has one.

    Returns:
    - dict: The context of the calling function.
    """

    # Get the current frame
    current_frame = inspect.currentframe()
    # Move one level up to the caller frame
    caller_frame = current_frame.f_back
    # Get the function object from the caller frame
    caller_function = caller_frame.f_globals[caller_frame.f_code.co_name]
    # Retrieve the context from the function object
    context = getattr(caller_function, "context", None)

    return context


@type_inference_decorator(needs_context=True)
def query_embedchain(query, data_source):
    """
    Send a query to embedchain and retrieve results.

    Args:
    - query (str): The question/query to be sent to embedchain.
    - data_source (str): URL or path to a data source to be added to embedchain before querying.

    Returns:
    - str: Result from embedchain.
    """

    os.environ["OPENAI_API_KEY"] = get_context()["openaikey"]
    embedchain_app = App()

    try:
        # Rely on Embedchain's automatic data type detection.
        embedchain_app.add(data_source)

        # Query the embedchain app
        result = embedchain_app.query(query)
    finally:
        del os.environ["OPENAI_API_KEY"]

    return result


# Unwrapped functions
def identity(x):
    return x
