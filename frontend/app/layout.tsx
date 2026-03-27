import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "mjsim — Prompt to Physics Simulation",
  description: "Generate MuJoCo physics simulations from text prompts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
