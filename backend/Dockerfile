# Small official Python image based on Debian
FROM python:3.12-slim

# Do not write .pyc files; send output straight to stdout without buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create an unprivileged user to run the app
RUN useradd --create-home --uid 10001 appuser

# Install dependencies first, so this layer is cached when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app.py .

# Drop root privileges
USER appuser

EXPOSE 5000

# Gunicorn: production server, 2 worker processes, access and error logs to stdout
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "app:app"]