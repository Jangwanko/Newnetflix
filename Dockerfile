FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV DJANGO_ALLOWED_HOSTS=localhost,web
ENV DJANGO_SECRET_KEY=your-secure-secret
ENV DJANGO_DEBUG=False

CMD ["/bin/sh", "/entrypoint.sh"]