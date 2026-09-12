FROM node:24.21.0-bookworm-slim

WORKDIR /app

RUN npm install --global npm@11.19.0

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]