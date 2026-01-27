# =============================================================================
# NexusAI Documentation - Docusaurus
# =============================================================================

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build the documentation
RUN npm run build

# =============================================================================
# Production stage - serve with nginx
# =============================================================================
FROM nginx:alpine AS production

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built documentation
COPY --from=builder /app/build /usr/share/nginx/html

# Create non-root user
RUN adduser -D -u 1001 docuser && \
    chown -R docuser:docuser /usr/share/nginx/html && \
    chown -R docuser:docuser /var/cache/nginx && \
    chown -R docuser:docuser /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R docuser:docuser /var/run/nginx.pid

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ || exit 1

EXPOSE 3000

USER docuser

CMD ["nginx", "-g", "daemon off;"]
