# Quant Trading Dashboard - Frontend Dockerfile
# Serves static HTML dashboards via Nginx

FROM nginx:alpine

# Copy dashboard files
COPY *.html /usr/share/nginx/html/
COPY *.json /usr/share/nginx/html/
COPY data/ /usr/share/nginx/html/data/
COPY quant2_data/ /usr/share/nginx/html/quant2_data/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create non-root user (nginx already runs as nginx user)
RUN chown -R nginx:nginx /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
