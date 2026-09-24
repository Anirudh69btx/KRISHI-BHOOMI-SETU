FROM node:20-alpine AS base

WORKDIR /app

COPY package.json ./

FROM base AS development
RUN npm install
COPY tsconfig.json ./
COPY src/ ./src/
EXPOSE 3001
CMD ["npm", "run", "dev"]

FROM base AS builder
RUN npm install
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY --from=builder /app/dist ./dist
EXPOSE 3001
CMD ["npm", "run", "start"]
