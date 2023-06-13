# Table of Contents

- [AI-Eye application](#ai-eye-application)
    - [Setting up with docker](#setting-up-with-docker)
        - [Prerequisites](#prerequisites)
        - [Starting the Project](#starting-the-project)
        - [Stopping the Project](#stopping-the-project)
        - [Creating a Database Backup](#creating-a-database-backup)
        - [Restoring the Database from a Backup](#restoring-the-database-from-a-backup)
        - [Creating a Superuser](#creating-a-superuser)
    - [Setting up without docker (for development purposes only, deprecated and not supported)](#setting-up-without-docker-for-development-purposes-only-deprecated-and-not-supported)
    - [Setting up users](#setting-up-users)
    - [Useful commands](#useful-commands)
    - [Prompts Overview](#prompts-overview)
    - [Builtin Functions Overview](#builtin-functions-overview)
    - [Pipelines Overview](#pipelines-overview)
    - [OpenAI API Overview](#openai-api-overview)
        - [openai endpoint](#openai-endpoint)
        - [cache endpoint](#cache-endpoint)
        - [API Endpoints](#api-endpoints)
            - [openai](#openai)
            - [cache](#cache)
    - [Pipeline API Overview](#pipeline-api-overview)
        - [pipeline_args](#pipeline_args)
        - [pipeline_call](#pipeline_call)

# AI-Eye application

## Setting up with docker

This guide explains how to manage the AI Eye application using Docker Compose and Makefile.

### Prerequisites

Before you start, you should have the following installed on your system:

- Docker
- Docker Compose
- Make (optional, for using the Makefile)

### Starting the Project

You can start the project using Docker Compose:

```bash
docker-compose up
```

Alternatively, you can use the Makefile:

```bash
make up
```

This will start the services in detached mode.

### Stopping the Project

You can stop the project using Docker Compose:

```bash
docker-compose down
```

Or with the Makefile:

```bash
make down
```

### Creating a Database Backup

Use the Makefile command:

```bash
make backup
```

This will create a backup of your PostgreSQL database in a file within the `backups` directory.

### Restoring the Database from a Backup

To restore the database from a backup file, use:

```bash
make restore file=<path-to-your-backup-file>
```

Replace `<path-to-your-backup-file>` with the actual path to your backup file.

### Creating a Superuser

You can create a Django superuser with the following command:

```bash
make create-admin
```

This will prompt you to enter the username, email (optional), and password for the superuser.


## Setting up without docker (for development purposes only, deprecated and not supported)

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

## Setting up users


From now on, to grant the `AIEYE_ADMINS` role to some users, follow these steps:
1. Go to Django Admin, i.e. http://127.0.0.1:8000/admin
2. Log in as a superuser
3. Navigate to `Home > Core > Users`, i.e. http://127.0.0.1:8000/admin/core/user/
4. Select a user you wish to grant the role to and click on it. A user edit form will appear
5. On the form, scroll down to the Permissions section and move the `AIEYE_ADMINS` value from the `Available Groups` text area to the `Chosen Groups` section.
6. Scroll to the bottom and press the `SAVE` button
7. You are done!

Open http://127.0.0.1:8000, it is where your `AIEYE_ADMINS` dashboard resides

## Useful commands:
```
(env) pre-commit run
```

## Prompts Overview
Prompts are a way to dynamically generate text with placeholders that can be replaced with user input. The syntax for a prompt is a string with curly braces {} containing an arbitrary name for the argument. For example, {name} can be used as a prompt for the user to enter their name. Prompt arguments should start with a letter and can be used in any order within the string.

Here's an example of a prompt in action:
```shell
    Hello, {name}! How are you today?
```

## Builtin Functions Overview
Built-in functions are like regular functions that can be invoked with arguments in the standard way, using the syntax function_name(argument1, argument2, ...). Unlike prompts, built-in functions don't use curly braces to denote arguments. They can accept any number of arguments, but they don't accept *args or **kwargs.
Built-in functions reside in the `funcs` package within the `builtins.py` Python script.

In addition to built-in functions, users can create their own functions and store them in the `funcs` package within Python scripts with names starting with `custom_`, such as `custom_funcs.py` or `custom_addons.py`, among others. These user-defined functions will be dynamically linked on demand.

To make built-in or user-defined functions visible to the codebase, an admin must register them in the Dashboard's built-ins section. Only users with the `AIEYE_ADMIN` role have the ability to register built-in functions. This dashboard section also allows for the synchronization of the currently available built-ins and user-defined functions, in case any have been added, removed, or introduced in a standalone Python script file following the procedure outlined above.

After a synchronization, a success message is displayed with information on the number of functions added or deleted. In addition, if any functions were created or deleted, a dynamic link with the text "Refresh page" is provided to refresh the current page.

An example of built-in function:
```shell
def foo(bar, fred):
    return f"{bar} and {fred}"
```

## Pipelines Overview
Pipelines are nested calls of prompts and/or built-in functions, where the output of one function is passed as input to another. The syntax for pipelines is similar to functional composition, where the output of the inner function becomes the input to the outer function.
An example of a pipeline is:
```shell
foo(bar(fred(1,2,3)))
```

In this example, the fred function takes in arguments (1,2,3), which is then passed as input to the bar function. The output of the bar function is then passed as input to the foo function. Pipelines can be used to compose complex operations from simple building blocks.

There are multiple ways to pass user-provided arguments to built-in functions and prompts.
Let's begin by discussing prompts.
If you have a prompt named `prompt_buddy` that looks like this:
```shell
Hey {buddy}
```
You can use it in a pipeline using one of the following methods:
```shell
prompt_buddy(buddy)
prompt_buddy(buddy=buddy_arg)
prompt_buddy(dude)
```
Here, `buddy_arg` is a named placeholder that is supplied through the Pipeline Execution Form.

The last example works for prompts having 1 argument only, i.e. currently it is not feasible to provide arbitrary
named arguments for a prompt that requires multiple arguments.
Let’s say prompt `p1` has one argument `a1`. The following is allowed:
```shell
p1(p1(p1(arg)))
```

The following is permissible, although it is excessively verbose:
```shell
`p1(a1=p1(a1=p1(a1=arg)))`
```

Moving on to built-in functions, let's consider a function named `builtin_hi`:
```shell
def builtin_hi(buddy):
    return f"Hi, {buddy}"
```
You can use this function in a pipeline using any of the following ways:
```shell
builtin_hi(buddy)
builtin_hi(buddy=buddy_arg)
builtin_hi(dude)
```
Here, `dude` and `buddy` are arguments passed directly to the function in place of `buddy`.
In contrast, `buddy_arg` is a named placeholder which is filled in through the Pipeline Execution Form.


# OpenAI API Overview

This Django project contains two endpoints for working with Open AI: openai and cache. They use HTTP Token based authentication.

## openai endpoint
The openai endpoint allows users to send requests to the OpenAI API and receive responses. The endpoint accepts the following methods:

    POST: Sends a request to the OpenAI API and returns a response.

## cache endpoint
The cache endpoint allows users to retrieve previously-cached responses to requests made to the OpenAI API. The endpoint accepts the following methods:

    POST: Retrieves a previously-cached response to a request made to the OpenAI API.

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

    endpoint (string): Required. The OpenAI API endpoint to request. The following OpenAI endpoints are currently supported: "v1/chat/completions", "v1/edits"
    parameters (dict): Required. The parameters to send with the request.

Response

    response (string): The response returned by the OpenAI API.

Example of usage:
```shell
curl --location 'http://127.0.0.1:8000/api/openai/v1/chat/completions/' \
--header 'Authorization: Bearer pubtokenpubtoken1pubtoken1pubtokenXXXXXX' \
--header 'Content-Type: application/json' \
--data '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Is blue a color for blind?"}]
}'

{"response":"As an AI language model, I cannot experience color since I don't have senses. However, people who are visually impaired may perceive colors differently based on their degree of blindness. Many individuals with low vision or partial sight can distinguish some colors, including blue, while others with complete blindness perceive no colors at all.","cache_hit":true}

```

### cache

POST /api/cache/{endpoint}/

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
curl --location 'http://127.0.0.1:8000/api/cache/v1/chat/completions/' \
--header 'Authorization: Bearer pubtokenpubtoken1pubtoken1pubtokenXXXXXX' \
--header 'Content-Type: application/json' \
--data '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Is blue a color for blind?"}]
}'

[{"response":"As an AI language model, I cannot experience color since I don't have senses. However, people who are visually impaired may perceive colors differently based on their degree of blindness. Many individuals with low vision or partial sight can distinguish some colors, including blue, while others with complete blindness perceive no colors at all.","cache_hit":true}]
```


# Pipeline API Overview
In addition to the previously mentioned APIs, the project includes two API endpoints for working with pipelines.

## pipeline_args
### GET /api/pipeline/args?pipeline_name={param}
Authenticated users can use this endpoint to send requests to the server for retrieving arguments of a specified pipeline and receive corresponding responses. The endpoint accepts the following methods:

    GET: Sends a request to the Django server and returns a response.

Example of usage:
```shell
curl --location 'http://127.0.0.1:8000/api/pipeline/args?pipeline_name=my_pipeline' --header 'Cookie: csrftoken=g69kAjkZan6yAGqD5VOGCUjbUdR1qPka; sessionid=97wvcm0t0t1rgrpsy38ordgtmh7cw9iz' --header 'Content-Type: text/plain'

{"success":true,"response":["s"]}
```

## pipeline_call
### POST /api/pipeline/call/
This endpoint enables authenticated users to send requests to the server for executing a specified pipeline and receive responses in return. The endpoint accepts the following methods:

    POST: Sends a request to the Django server and returns a response.
This endpoint accepts either Session authentication or HTTP Token based authorization.

Example of usage (with Session authentication):
```shell
curl --location 'http://127.0.0.1:8000/api/pipeline/call' \
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
curl --location 'http://127.0.0.1:8000/api/pipeline/call' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer pubtokenpubtoken1pubtoken1pubtoken111111' \
--data '{
    "pipeline_id": 14,
    "args": {"s": "abc"}
}'
{"success":true,"response":"abc"}
```
