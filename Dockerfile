FROM python:3.9-slim

WORKDIR /app

COPY ./app/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

# Change this line - remove "app." prefix since we're already in the app directory
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
