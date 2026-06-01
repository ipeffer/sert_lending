FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY samples /samples

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
