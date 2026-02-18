import Nav from '../../components/Nav';
import { getProducts } from '../../lib/demoData';

export default function ProductPage() {
  const product = getProducts()[0];

  return (
    <main>
      <Nav />
      <section className="max-w-5xl mx-auto p-6">
        <div className="bg-white border rounded-2xl shadow-sm grid grid-cols-1 md:grid-cols-2 overflow-hidden">
          <img src={product.image} alt={product.name} className="w-full h-80 md:h-full object-cover" />
          <div className="p-6 space-y-4">
            <h1 className="text-3xl font-bold">{product.name}</h1>
            <p className="text-slate-600">{product.description}</p>
            <div className="text-2xl font-bold text-blue-700">${product.price}</div>
            <ul className="text-sm text-slate-600 space-y-1 list-disc pl-5">
              <li>1 year warranty</li>
              <li>Fast shipping available</li>
              <li>Secure checkout</li>
            </ul>
            <button className="mt-2 bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700">Add to cart</button>
          </div>
        </div>
      </section>
    </main>
  );
}
