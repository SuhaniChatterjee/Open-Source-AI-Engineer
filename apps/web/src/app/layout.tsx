import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenSource AI Engineer",
  description: "Understand any GitHub repository in minutes.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-border bg-panel/60 backdrop-blur sticky top-0 z-10">
            <div className="mx-auto max-w-6xl px-6 py-3 flex items-center gap-3">
              <a href="/" className="flex items-center gap-2">
                <span className="inline-block h-6 w-6 rounded bg-gradient-to-br from-accent to-accent2" />
                <span className="font-semibold tracking-tight">
                  OpenSource AI Engineer
                </span>
              </a>
              <span className="badge bg-panel2 text-muted ml-2">MVP</span>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
