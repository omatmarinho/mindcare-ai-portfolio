# Imagem do frontend Next.js do MindCare AI (build em duas etapas)

# 1) Build
FROM node:24-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build \
 && cp -r public .next/standalone/ \
 && cp -r .next/static .next/standalone/.next/

# 2) Execução: só o servidor enxuto gerado pelo build
FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
USER node
EXPOSE 3000
CMD ["node", "server.js"]
