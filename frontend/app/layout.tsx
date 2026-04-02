import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SimGen — Prompt to Physics Simulation",
  description: "Generate MuJoCo physics simulations from text prompts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-[#0f1115] text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
