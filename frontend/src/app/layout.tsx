import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MindCare AI",
  description: "Gestão de consultório para psicólogos",
  // Páginas com dados de pacientes não devem aparecer em buscadores
  robots: { index: false, follow: false },
};

// Cor da barra do navegador no celular: o mesmo creme-sálvia do fundo
export const viewport: Viewport = {
  themeColor: "#edefe9",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
