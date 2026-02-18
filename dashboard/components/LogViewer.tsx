'use client';
import { useEffect, useRef } from 'react';

export default function LogViewer({ content }: { content: string }) {
  const ref = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [content]);

  return <pre ref={ref} className="bg-black text-green-300 p-3 rounded h-96 overflow-auto text-xs">{content || 'No log selected'}</pre>;
}
