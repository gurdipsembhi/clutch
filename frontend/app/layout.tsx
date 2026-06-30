import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clutch — Your AI Last-Minute Life Saver",
  description:
    "An autonomous productivity agent that prioritizes your tasks, builds a time-blocked schedule, breaks down what's at risk, and drafts what you need to send — before deadlines slip.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
