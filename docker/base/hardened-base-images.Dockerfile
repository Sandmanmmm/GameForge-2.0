# Hardened Base Images - Alpine/Distroless Strategy
# =================================================

# 1. Python AI Services - Distroless Base (Smallest attack surface)
FROM python:3.11-alpine AS python-base-alpine
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && rm -rf /var/cache/apk/*

FROM gcr.io/distroless/python3-debian12:nonroot AS python-base-distroless
COPY --from=python-base-alpine /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base-alpine /usr/local/bin /usr/local/bin

# 2. Python GPU Services - Minimal CUDA Alpine
FROM nvidia/cuda:12.1-runtime-alpine3.18 AS gpu-base-alpine
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    && rm -rf /var/cache/apk/*

# 3. Node.js Frontend - Already using Alpine (Good!)
FROM node:20-alpine AS node-base-alpine
RUN apk add --no-cache \
    dumb-init \
    && rm -rf /var/cache/apk/*

# 4. Nginx - Distroless
FROM nginx:alpine AS nginx-base-alpine
RUN rm -rf /var/cache/apk/*

FROM gcr.io/distroless/base-debian12:nonroot AS nginx-base-distroless
COPY --from=nginx-base-alpine /usr/sbin/nginx /usr/sbin/nginx
COPY --from=nginx-base-alpine /etc/nginx /etc/nginx
COPY --from=nginx-base-alpine /var/lib/nginx /var/lib/nginx

# 5. Database Services - Official Alpine images preferred
# PostgreSQL: postgres:16-alpine
# Redis: redis:7-alpine
# MongoDB: mongo:7-alpine (when needed)

# 6. Monitoring Stack - Alpine variants
FROM prom/prometheus:latest AS prometheus-base
FROM grafana/grafana:latest-alpine AS grafana-base
FROM quay.io/prometheus/node-exporter:latest AS node-exporter-base