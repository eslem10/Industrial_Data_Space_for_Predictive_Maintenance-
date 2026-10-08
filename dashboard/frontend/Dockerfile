FROM node:22-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api
ARG VITE_EDC_F1_URL=http://localhost:19193/management/v3
ARG VITE_EDC_F2_URL=http://localhost:21193/management/v3
ARG VITE_EDC_F3_URL=http://localhost:23193/management/v3
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_EDC_F1_URL=$VITE_EDC_F1_URL \
    VITE_EDC_F2_URL=$VITE_EDC_F2_URL \
    VITE_EDC_F3_URL=$VITE_EDC_F3_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
