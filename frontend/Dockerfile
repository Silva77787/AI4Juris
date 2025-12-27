FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_BASE=/
ARG VITE_API_URL=http://localhost:7777
ENV VITE_BASE=$VITE_BASE
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app
RUN npm install -g serve

COPY --from=build /app/dist ./dist

EXPOSE 4173

CMD ["serve", "-s", "dist", "-l", "4173"]
