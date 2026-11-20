import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// Política de conteúdo (CSP): o navegador só carrega scripts, estilos, imagens e
// conexões do próprio Psinara. Mesmo que algum texto malicioso fosse parar na
// página, ele não conseguiria buscar código ou enviar dados para outro site.
// Sem "nonce" para manter as páginas estáticas (ver guia de CSP do Next.js).
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "media-src 'self' blob:", // pré-escuta do áudio gravado no navegador
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

// Cabeçalhos de segurança enviados em todas as páginas
const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  // Não envia o endereço da página para outros sites (os links de e-mail têm tokens na URL)
  { key: "Referrer-Policy", value: "no-referrer" },
  // Impede que o Psinara seja exibido dentro de outro site (clickjacking)
  { key: "X-Frame-Options", value: "DENY" },
  // O navegador não deve "adivinhar" o tipo dos arquivos
  { key: "X-Content-Type-Options", value: "nosniff" },
  // Microfone liberado só para o próprio site (gravação de sessões no futuro)
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
];

const nextConfig: NextConfig = {
  // No Docker (NEXT_OUTPUT=standalone) gera um servidor enxuto, sem node_modules inteiro.
  // Fica desligado no Windows, onde exigiria permissão para criar links simbólicos.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  cacheComponents: true,
  // Esconde o selo do modo de desenvolvimento (erros continuam aparecendo)
  devIndicators: false,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  experimental: {
    // Áudios de sessão podem ter dezenas de MB (o backend aceita até 100 MB)
    serverActions: { bodySizeLimit: "100mb" },
    proxyClientMaxBodySize: "100mb",
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
