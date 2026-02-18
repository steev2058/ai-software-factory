import './globals.css';
import type { Metadata } from 'next';
import { defaultSEO } from '../lib/seo';
export const metadata: Metadata = { title: defaultSEO.title, description: defaultSEO.description };
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
