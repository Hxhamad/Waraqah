import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Waraqah - AI Stock Analyzer",
  description: "Agentic market research platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
