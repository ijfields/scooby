import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
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
  title: "Scooby — Your stories deserve to be seen",
  description:
    "Turn your stories into stunning 60-second vertical drama videos. Write, edit scenes, choose a style, and export — no production skills needed.",
  openGraph: {
    title: "Scooby — Your stories deserve to be seen",
    description:
      "Turn your stories into stunning 60-second vertical drama videos. No production skills needed.",
    type: "website",
    locale: "en_US",
    siteName: "Scooby",
  },
  twitter: {
    card: "summary_large_image",
    title: "Scooby — Your stories deserve to be seen",
    description:
      "Turn your stories into stunning 60-second vertical drama videos.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col">{children}</body>
      </html>
    </ClerkProvider>
  );
}
