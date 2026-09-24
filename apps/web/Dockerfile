FROM node:20-alpine AS base

WORKDIR /app

COPY package.json ./

FROM base AS development
RUN npm install
COPY tsconfig.json vite.config.ts tailwind.config.ts postcss.config.js index.html ./
COPY src/ ./src/
COPY public/ ./public/
EXPOSE 5173 5174
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS builder
RUN npm install
COPY tsconfig.json vite.config.ts tailwind.config.ts postcss.config.js index.html ./
COPY src/ ./src/
COPY public/ ./public/
RUN npm run build

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
