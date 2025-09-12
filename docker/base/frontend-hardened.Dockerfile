# Hardened Frontend Dockerfile (Alpine + Distroless)
# Multi-stage build for minimal production image

# Build stage - Node Alpine
FROM node:20-alpine AS builder
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Copy package files
COPY package*.json ./
RUN npm ci --only=production --silent

# Copy source and build
COPY src/ ./src/
COPY public/ ./public/
COPY *.config.* ./
RUN npm run build

# Production stage - Distroless with static content
FROM gcr.io/distroless/nodejs20-debian12:nonroot AS production

# Copy built application
COPY --from=builder --chown=nonroot:nonroot /app/dist /app/dist
COPY --from=builder --chown=nonroot:nonroot /app/node_modules /app/node_modules
COPY --from=builder --chown=nonroot:nonroot /app/package.json /app/

WORKDIR /app

# Security: Non-root user (distroless default)
USER nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["node", "-e", "require('http').get('http://localhost:3000/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1))"]

# Run application
EXPOSE 3000
CMD ["node", "dist/server.js"]

# Alternative: Static file serving with nginx distroless
FROM gcr.io/distroless/base-debian12:nonroot AS static

# Copy built files
COPY --from=builder --chown=nonroot:nonroot /app/dist /usr/share/nginx/html/
COPY --from=nginx:alpine /etc/nginx/nginx.conf /etc/nginx/
COPY --from=nginx:alpine /usr/sbin/nginx /usr/sbin/

USER nonroot
EXPOSE 80
CMD ["/usr/sbin/nginx", "-g", "daemon off;"]