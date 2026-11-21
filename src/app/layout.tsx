import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Amiri } from "next/font/google";
import { PreviewNotice } from "@/components/PreviewNotice";
import { CrawlPolicy, PrivatePreviewBanner, SiteFooter } from "@/components/archive/SiteChrome";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

// Font variables sit on <html> because design-tokens.css resolves them at :root (DESIGN.md §Typography).
const inter = Inter({
  variable: "--font-inter-face",
  subsets: ["latin"],
  axes: ["opsz"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono-face",
  subsets: ["latin"],
});

const amiri = Amiri({
  variable: "--font-amiri-face",
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
  // No theme class: the tokens follow the visitor's system setting (DESIGN.md §Tokens, owner decision).
  return (
    <html lang="en" className={`${inter.variable} ${jetBrainsMono.variable} ${amiri.variable}`}>
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:start-2 focus:top-2 focus:z-[60] focus:bg-paper focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-ink"
        >
          Skip to content
        </a>
        <PrivatePreviewBanner />
        <CrawlPolicy />
        <SiteHeader />
        <PreviewNotice />
        <div id="main-content" tabIndex={-1} className="outline-none">
          {children}
        </div>
        <SiteFooter />
      </body>
    </html>
  );
}
