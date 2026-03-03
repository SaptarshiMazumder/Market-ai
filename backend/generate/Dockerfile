FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p generated

EXPOSE 5008

CMD ["gunicorn", "--bind", "0.0.0.0:5008", "--workers", "2", "--timeout", "300", "app:app"]
