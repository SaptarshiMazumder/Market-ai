FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p videos

EXPOSE 5006

CMD ["gunicorn", "--bind", "0.0.0.0:5006", "--workers", "2", "--timeout", "600", "app:app"]
