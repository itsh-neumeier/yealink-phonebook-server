FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/ftp/phonebooks /app/instance && chown -R appuser:appuser /data /app

USER appuser

EXPOSE 8080 2121

CMD ["python", "-m", "app.main"]