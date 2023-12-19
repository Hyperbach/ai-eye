FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y docker.io
RUN apt-get install -y libffi-dev

WORKDIR /ai-eye
RUN mkdir eval

COPY requirements.txt /ai-eye/

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn
RUN pip install docker

# Copy project
COPY . /ai-eye/

RUN python manage.py collectstatic --noinput
