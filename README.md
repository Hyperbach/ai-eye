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
(env) python manage.py wait_for_db
```

## TO BE CONTINUED
