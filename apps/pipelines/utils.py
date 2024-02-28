import json
import re


def find_first(predicate, src_coll):
    return next(filter(predicate, src_coll), None)


def extract_json_objects(text, decoder=json.JSONDecoder()):
    """Find JSON objects in text, and yield the decoded JSON data."""
    pos = 0
    while True:
        match = text.find('{', pos)
        if match == -1:  # No more JSON objects
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            yield result
            pos = match + index  # Move past the current JSON object
        except ValueError:
            pos = match + 1  # Move to the next character and try again


def strip_json_response(input_str, strict=False):
    """
    Processes a string containing potential JSON data and returns a formatted JSON string.

    In non-strict mode, the function will attempt to detect and format JSON data that is either:
    - Directly provided as a valid JSON string.
    - Wrapped in a specific format with ```json ... ``` markers.
    If the JSON is wrapped and isolated (no additional text outside the markers), it will be extracted,
    validated, and returned in a pretty-printed format. If the input is invalid JSON or not wrapped correctly,
    the original input string is returned as is.

    In strict mode, the function focuses solely on extracting and formatting the first valid JSON object
    found in the input string, ignoring all other content. If no valid JSON can be extracted, an empty
    JSON object ({}) is returned.

    Parameters:
    - input_str (str): The string to be processed, which may contain JSON data.
    - strict (bool): A boolean flag that indicates whether to operate in strict mode. Defaults to False.

    Returns:
    - A formatted JSON string if valid JSON is found; otherwise, depending on the mode, either the original
      input (non-strict mode) or an empty JSON object (strict mode).
    """

    # Try to directly convert the input string to JSON and reformat it.
    try:
        return json.dumps(json.loads(input_str), indent=4)
    except json.JSONDecodeError:
        # Non-strict mode adjustments
        if not strict:
            # Check if the JSON is wrapped and isolated
            wrapped_json_match = re.search(r'^\s*```\s*json\s*([\s\S]*?)\s*```\s*$', input_str, re.DOTALL)
            if wrapped_json_match:
                # Extract and attempt to reformat only the JSON part
                json_str = wrapped_json_match.group(1)
                try:
                    return json.dumps(json.loads(json_str), indent=4)
                except json.JSONDecodeError:
                    pass  # If JSON is invalid, proceed to return the string as is.
            # Return the original string if no valid, isolated wrapped JSON is found
            return input_str
        else:
            try:
                # Try finding any valid JSON structure in the string.
                for obj in extract_json_objects(input_str):
                    return json.dumps(obj, indent=4)  # Return the first valid JSON object found.
            except json.JSONDecodeError:
                pass  # If no valid JSON is found, proceed to the next step.
            # Return an empty JSON object if no valid JSON was found.
            return '{}'


def _test(test_name, function_call, expected_result):
    print(f"Test Name: {test_name}")
    result = function_call
    print(f"Result: {result}")
    print(f"Expected: {expected_result}")
    assert result == expected_result, f"{test_name} failed"
    print(f"{test_name} passed\n")


# Tests for extract_json_objects
test_cases = [
    ("Valid JSON and nothing else", list(extract_json_objects('{"key": "value"}')), [{"key": "value"}]),
    ("Prefixed with junk", list(extract_json_objects('Random text before {"key": "value"}')), [{"key": "value"}]),
    ("Postfixed with junk", list(extract_json_objects('{"key": "value"} Random text after')), [{"key": "value"}]),
    ("Prefixed and postfixed", list(extract_json_objects('Junk before {"key": "value"} Junk after')),
     [{"key": "value"}]),
    ("Starts as JSON and ends abruptly", list(extract_json_objects('{"key": "value')), []),  # Incomplete JSON
    ("Contains multiple JSONs", list(extract_json_objects('{"key1": "value1"}{"key2": "value2"}')),
     [{"key1": "value1"}, {"key2": "value2"}]),
]

for name, func_call, expected in test_cases:
    _test(name, func_call, expected)

# Tests for strip_json_response in non-strict mode
_test("Non-strict: Unwrapped JSON", strip_json_response('{"key": "value"}', strict=False),
      json.dumps({"key": "value"}, indent=4))
_test("Non-strict: Wrapped JSON", strip_json_response('\n```json\n{"key": "value"}\n```\n', strict=False),
      json.dumps({"key": "value"}, indent=4))
_test("Non-strict: Unwrapped JSON in the middle of text",
      strip_json_response('Random text before {"key": "value"} Random text after', strict=False),
     'Random text before {"key": "value"} Random text after')
_test("Non-strict: Wrapped JSON in the middle of text",
      strip_json_response('Random text before ```json\n{"key": "value"}\n``` Random text after', strict=False),
     'Random text before ```json\n{"key": "value"}\n``` Random text after')
_test("Non-strict: Invalid wrapped JSON", strip_json_response('```json\n{"key": ', strict=False), '```json\n{"key": ')
_test("Non-strict: Invalid unwrapped JSON surrounded by text",
      strip_json_response('Random text before {"key": Random text after', strict=False),
     'Random text before {"key": Random text after')

# Tests for strip_json_response in strict mode
_test("Strict: Unwrapped JSON", strip_json_response('{"key": "value"}', strict=True),
      json.dumps({"key": "value"}, indent=4))
_test("Strict: Wrapped JSON", strip_json_response('```json\n{"key": "value"}\n```', strict=True),
      json.dumps({"key": "value"}, indent=4))
_test("Strict: Unwrapped JSON in the middle of text",
      strip_json_response('Random text before {"key": "value"} Random text after', strict=True),
      json.dumps({"key": "value"}, indent=4))
_test("Strict: Wrapped JSON in the middle of text",
      strip_json_response('Random text before ```json\n{"key": "value"}\n``` Random text after', strict=True),
      json.dumps({"key": "value"}, indent=4))
_test("Strict: Invalid wrapped JSON", strip_json_response('```json\n{"key": ', strict=True), '{}')
_test("Strict: Invalid unwrapped JSON surrounded by text",
      strip_json_response('Random text before {"key": Random text after', strict=True), '{}')

print("All tests passed successfully!")
