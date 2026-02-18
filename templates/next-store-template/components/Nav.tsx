import Link from 'next/link';

export default function Nav() {
  return (
    <nav className="p-4 bg-white border-b sticky top-0 z-10">
      <div className="max-w-6xl mx-auto flex items-center gap-4 text-sm sm:text-base">
        <Link href="/" className="hover:text-blue-600">Home</Link>
        <span className="text-slate-300">|</span>
        <Link href="/product" className="hover:text-blue-600">Product</Link>
        <span className="text-slate-300">|</span>
        <Link href="/cart" className="hover:text-blue-600">Cart</Link>
      </div>
    </nav>
  );
}
