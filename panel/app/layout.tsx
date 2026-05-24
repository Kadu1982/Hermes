import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hermes Panel",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui", margin: 0, padding: 0 }}>{children}</body>
    </html>
  );
}
