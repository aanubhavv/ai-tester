import type { Metadata } from "next";
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

import Sidebar from "@/components/layout/sidebar";
import { GlobalUIProvider } from "@/components/ui/GlobalUIProvider";

export const metadata: Metadata = {
  title: "QAForge",
  description: "Enterprise AI QA Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="flex h-full bg-zinc-900 text-zinc-50 overflow-hidden">
        <GlobalUIProvider>
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-zinc-50 text-zinc-950 dark:bg-black dark:text-zinc-50">
            {children}
          </main>
        </GlobalUIProvider>
      </body>
    </html>
  );
}
