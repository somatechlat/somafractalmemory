# Minimal Dockerfile to run the FastAPI example
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY api-requirements.txt /app/api-requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/api-requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "examples.api:app", "--host", "0.0.0.0", "--port", "8000"]

