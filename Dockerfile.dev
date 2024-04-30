FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y docker.io

WORKDIR /ai-eye
RUN mkdir eval

COPY requirements.txt /ai-eye/
COPY requirements.dev.txt /ai-eye/
RUN pip install --no-cache-dir -r requirements.txt -r requirements.dev.txt

RUN pip install docker

# Copy project
COPY . /ai-eye/
