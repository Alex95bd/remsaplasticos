FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --uid 1000 remsa

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=remsa:remsa . .
RUN chmod +x docker/entrypoint.sh \
    && DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && mkdir -p /app/media && chown -R remsa:remsa /app/media /app/staticfiles

USER remsa
EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
