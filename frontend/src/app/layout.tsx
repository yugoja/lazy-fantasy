import '@/lib/sentry';
import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import Header from "@/components/Header";
import InstallPrompt from "@/components/InstallPrompt";
import NotificationPermission from "@/components/NotificationPermission";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "sonner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Lazy Fantasy - Fantasy Cricket League",
  description: "Predict match outcomes, compete with friends, and climb the leaderboard",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Lazy Fantasy",
  },
  icons: {
    apple: "/icons/icon-192x192.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${spaceGrotesk.variable}`}>
      <body className={inter.className}>
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
        <Script id="sw-register" strategy="afterInteractive">
          {`if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');`}
        </Script>
        <AuthProvider>
          <Header />
          <main className="pb-20">{children}</main>
          <InstallPrompt />
          <NotificationPermission />
          <Toaster position="top-center" richColors />
        </AuthProvider>
      </body>
    </html>
  );
}
