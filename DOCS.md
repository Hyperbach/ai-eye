# API Overview

This Django project contains two endpoints: openai and cache. They use HTTP Token based authorization.

## openai endpoint
The openai endpoint allows users to send requests to the OpenAI API and receive responses. The endpoint accepts the following methods:

    POST: Sends a request to the OpenAI API and returns a response.

## cache endpoint
The cache endpoint allows users to retrieve previously-cached responses to requests made to the OpenAI API. The endpoint accepts the following methods:

    GET: Retrieves a previously-cached response to a request made to the OpenAI API.

## API Endpoints
### openai

POST /api/openai/{endpoint}/

This endpoint sends a request to the OpenAI API and returns a response. It accepts a JSON body containing any parameters accepted by OpenAI.
The endpoint uses Token Based HTTP Authentication with Bearer key. When called, it responds with a JSON object having the following format:
```shell
{
    "response": "text",
    "cache_hit": {true|false}
}
```

The response field contains the response text from OpenAI. The cache_hit field is a boolean that is true if there was a hit in the database (see table Logs), false otherwise.

Request

    endpoint (string): Required. The OpenAI API endpoint to request. The following OpenAI endpoints are currently supported: "v1/completions", "v1/edits"
    parameters (dict): Required. The parameters to send with the request.

Response

    response (string): The response returned by the OpenAI API.

Example of usage:
```shell
curl -X POST 'http://127.0.0.1:8000/api/openai/v1/completions/' --header 'Authorization: Bearer pubtokenpubtoken1pubtoken1pubtokenXXXXXX' --header 'Content-Type: application/json' --data-raw '{
    "model":"text-davinci-003",
    "prompt":"is John a cool name??"
}'

{"response":"Yes, John is a cool name.","cache_hit":true}
```

### cache

GET /api/cache/{endpoint}/

This endpoint retrieves a previously-cached responses to a request made to the OpenAI API with a provided endpoint and query parameters.
The endpoint uses Token Based HTTP Authentication with Bearer key. When called, it responds with a JSON object having the following format:
```shell
[{"response": "text","cache_hit": {true|false}]
```
Request

    endpoint (string): Required. The OpenAI API endpoint that was requested.
    parameters (dict): Required. The parameters that were sent with the request.

Response

    response (string): The cached response returned by the OpenAI API.

Example of usage:
```shell
curl -X GET -G http://127.0.0.1:8000/api/cache/v1/completions/ --header 'Authorization: Bearer pubtokenpubtoken1pubtoken1pubtokenXXXXXX' --data-urlencode "prompt=is John a cool name??" --data-urlencode "model=text-davinci-003"

[{"response":"Yes, John is a cool name.","cache_hit":true}]
```
