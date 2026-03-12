FROM nginx:1.27-alpine

COPY docker/frontend/default.conf /etc/nginx/conf.d/default.conf
