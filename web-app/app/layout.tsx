import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "MTG Card Search",
  description: "Search for Magic: The Gathering cards",
  icons: {
    icon: "/favicon.png",
  },
};

export default function RootLayout({
  children,
  modal,
}: Readonly<{
  children: React.ReactNode;
  // Parallel route slot for intercepted card details, rendered above the
  // page. Resolves to null via @modal/default.tsx on ordinary routes.
  modal: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} antialiased`}>
        {children}
        {modal}
      </body>
    </html>
  );
}
