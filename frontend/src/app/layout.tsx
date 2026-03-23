import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeepDive AI — Real-Time Research Assistant",
  description:
    "Upload documents, process them into a vector database in real-time, and chat with an AI research assistant that cites its sources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen antialiased">
        <div className="gradient-bg" />
        {children}
      </body>
    </html>
  );
}
