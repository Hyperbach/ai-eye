# AI-Eye application

## Setup

Create a virtual environment to install dependencies in and activate it:

```shell
$ git clone https://github.com/Hyperbach/ai-eye
$ cd ai-eye
```

```shell
$ python -m venv venv
$ source venv/bin/activate
```

Install project dependencies only (i.e. no dev. requirements):
```shell
(venv) pip install -r requirements.txt
```
or

Install project dependencies along with dev dependencies for local setup:
```shell
(venv) pip install -r requirements.dev.txt
```

Setup settings:
```shell
$ touch .env
```
Please refer to the `example.env` file for details.

Once `pip` has finished downloading the dependencies:
```shell
(env) python manage.py migrate
(env) python manage.py createsuperuser
(env) python manage.py runserver
```

From now on, to grant the `AIEYE_ADMINS` role to some users, follow these steps:
1. Go to Django Admin, i.e. http://127.0.0.1:8000/admin
2. Log in as a superuser
3. Navigate to `Home > Core > Users`, i.e. http://127.0.0.1:8000/admin/core/user/
4. Select a user you wish to grant the role to and click on it. A user edit form will appear
5. On the form, scroll down to the Permissions section and move the `AIEYE_ADMINS` value from the `Available Groups` text area to the `Chosen Groups` section.
6. Scroll to the bottom and press the `SAVE` button
7. You are done!

Open http://127.0.0.1:8000, it is where your `AIEYE_ADMINS` dashboard resides

Run tests:
```shell
(env) python manage.py test
```

Code coverage:
```shell
(env) coverage run --source='.' manage.py test
(env) coverage report
(env) coverage html
```

Useful commands:
```
(env) pre-commit run
```

# OpenAI API Overview

This Django project contains two endpoints for working with Open AI: openai and cache. They use HTTP Token based authentication.

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


# Pipeline API Overview
In addition to the previously mentioned APIs, the project includes two API endpoints for working with pipelines.

## pipeline_args
### GET /api/pipeline/args?pipeline_id={param}
Authenticated users can use this endpoint to send requests to the server for retrieving arguments of a specified pipeline and receive corresponding responses. The endpoint accepts the following methods:

    GET: Sends a request to the Django server and returns a response.

Example of usage:
```shell
curl --location 'http://127.0.0.1:8000/api/pipeline/args?pipeline_id=14' --header 'Cookie: csrftoken=g69kAjkZan6yAGqD5VOGCUjbUdR1qPka; sessionid=97wvcm0t0t1rgrpsy38ordgtmh7cw9iz' --header 'Content-Type: text/pl

{"success":true,"response":["s"]}
```

## pipeline_call
### POST /api/pipeline/call/
This endpoint enables authenticated users to send requests to the server for executing a specified pipeline and receive responses in return. The endpoint accepts the following methods:

    POST: Sends a request to the Django server and returns a response.
This endpoint accepts either Session authentication or HTTP Token based authorization.

Example of usage (with Session authentication):
```shell
curl --location 'http://127.0.0.1:8000/api/pipeline/call/' \
--header 'Content-Type: application/json' \
--header 'X-CSRFToken: g69kAjkZan6yAGqD5VOGCUjbUdR1qPka' \
--header 'Cookie: csrftoken=g69kAjkZan6yAGqD5VOGCUjbUdR1qPka; sessionid=97wvcm0t0t1rgrpsy38ordgtmh7cw9iz' \
--data '{
    "pipeline_id": 14,
    "args": {"s": "abc"},
    "openaikey_id": 1
}'
{"success":true,"response":"abc"}
```

Example of usage (with HTTP Token based authentication):
```shell
curl --location 'http://127.0.0.1:8000/api/pipeline/call/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer pubtokenpubtoken1pubtoken1pubtoken111111' \
--data '{
    "pipeline_id": 14,
    "args": {"s": "abc"}
}'
{"success":true,"response":"abc"}
```
