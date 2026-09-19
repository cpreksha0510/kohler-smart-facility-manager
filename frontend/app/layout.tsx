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

export const metadata: Metadata = {
  title: "KOHLER Smart Facility Monitor — Airport Restroom Operations",
  description: "Terminal 2 multi-signal telemetry, anomaly detection, and AI explainability command center.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}>
      <body className="min-h-full bg-[#0D1117] text-[#F0F6FC] selection:bg-[#6B8CAE]/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
