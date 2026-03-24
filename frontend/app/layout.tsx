import "./globals.css";

import type { Metadata } from "next";


export const metadata: Metadata = {
  title: "Uliya Agent MVP",
  description: "A modular Deep Agents style web app MVP with FastAPI and Next.js.",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
