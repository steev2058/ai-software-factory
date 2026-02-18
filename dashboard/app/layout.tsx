import './globals.css';
import Link from 'next/link';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="bg-white border-b px-4 py-3 flex justify-between">
          <Link href="/dashboard" className="font-semibold">Factory Dashboard</Link>
          <span className="text-sm text-slate-500">Auto-refresh every 8s</span>
        </header>
        {children}
      </body>
    </html>
  );
}
