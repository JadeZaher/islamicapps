import type { Metadata } from "next";
import { Geist, Geist_Mono, Amiri } from "next/font/google";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const amiri = Amiri({
  variable: "--font-amiri",
  subsets: ["arabic", "latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "Shura wa Istehsan",
    template: "%s | Shura wa Istehsan",
  },
  description:
    "A hadith and narrator archive across the Sunni, Imami, Zaydi and Ibadi traditions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${amiri.variable} antialiased`}
      >
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
