FROM python:3.12.16-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app app

COPY requirements.txt requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock

COPY --chown=app:app . .

RUN mkdir -p /app/private_media /app/staticfiles \
    && chmod +x /app/docker/entrypoint.prod.sh \
    && chown -R app:app /app/private_media /app/staticfiles

USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
