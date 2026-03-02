// 2025-02-26
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import AppShell from "@/components/AppShell";
import { RadioProvider } from "@/components/RadioProvider";
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
  title: "Civic-one | One City One Number",
  description: "Unified City Emergency & Civic Dispatch Command Dashboard – One City One Number",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <RadioProvider>
          <AppShell>{children}</AppShell>
        </RadioProvider>
      </body>
    </html>
  );
}
