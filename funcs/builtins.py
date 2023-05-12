import datetime

import pytz


# example of builtin function
def concat(arg1, arg2) -> str:
    return f"{arg1} {arg2}"


# example of builtin function
def now(timezone) -> str:
    tz = pytz.timezone(timezone)
    return str(datetime.datetime.now(tz=tz))


# example of builtin function
def identity(s: str) -> str:
    return s
