# Nginx that runs as a non-root user and listens on port 8080
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Put our page where Nginx serves files from
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 8080