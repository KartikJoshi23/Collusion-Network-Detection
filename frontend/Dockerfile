# Frontend demo image (docs/deployment.md §2): build the static bundle, serve
# it with nginx, proxy /api to the api container. Multi-stage keeps the runtime
# image tiny (nginx + static assets only).
FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
