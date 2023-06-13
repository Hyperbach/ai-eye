FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /ai-eye

COPY requirements.txt /ai-eye/
COPY requirements.dev.txt /ai-eye/
RUN pip install --no-cache-dir -r requirements.txt -r requirements.dev.txt

# Copy project
COPY . /ai-eye/
