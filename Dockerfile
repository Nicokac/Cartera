FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Contenedor orientado a desarrollo/testing local, no a distribución final.
CMD ["python", "-m", "unittest", "tests.test_generate_real_report_split_runtime", "-v"]
