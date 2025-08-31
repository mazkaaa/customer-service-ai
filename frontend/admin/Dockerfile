# ── Stage 1: build the app ---------------------------------
FROM node:22 AS builder

ARG NODE_ENV=production
ENV NODE_ENV=$NODE_ENV

WORKDIR /app

# 1. Copy package files
COPY package.json package-lock.json ./

# 2. Clean install dependencies
RUN npm ci --omit=dev

# 3. Copy source & build
COPY . .
RUN npm run build

# ── Stage 2: serve with nginx ------------------------------
FROM nginx:stable-alpine AS runtime

# 4. Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# 5. Optional SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
