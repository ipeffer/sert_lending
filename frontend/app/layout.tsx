import type { Metadata } from "next";
import "./globals.css";
import { IframeResize } from "@/components/IframeResize";
import { TestModeBanner } from "@/components/TestModeBanner";

export const metadata: Metadata = {
  title: "Купить подарочный сертификат — Тестовая СПА продажа",
  description: "Подарочный сертификат — тестовая витрина продажи сертификатов СПА",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&subset=latin,cyrillic"
          rel="stylesheet"
        />
      </head>
      <body>
        <IframeResize />
        <TestModeBanner />
        {children}
      </body>
    </html>
  );
}
