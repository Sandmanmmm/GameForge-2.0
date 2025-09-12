# Frontend Service Dockerfile
FROM ghcr.io/sandmanmmm/ai-game-production-p/base-node:latest

# Copy frontend source
COPY src/frontend/web/ ./
COPY package*.json ./

# Build frontend
RUN npm run build

# Copy built assets
COPY --from=builder /app/dist ./dist

# Expose port
EXPOSE 3000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

CMD ["npm", "start"]