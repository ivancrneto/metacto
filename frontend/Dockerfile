FROM node:22-alpine AS build
# Use the pnpm version pinned in package.json's "packageManager" field, and let
# corepack fetch it without an interactive prompt — keeps host/container in sync.
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
# The API base URL is baked into the static bundle at build time.
ARG VITE_API_BASE_URL=http://localhost:8010
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
