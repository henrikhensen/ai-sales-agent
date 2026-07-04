FROM node:20-alpine

WORKDIR /app

# Browser-side requests must reach a URL the host machine can resolve, so the
# published backend port (not an internal Docker service name) is the correct
# default for a local docker-compose setup.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
