import Nav from '../components/Nav';
import { getProducts } from '../lib/demoData';

export default function HomePage() {
  const products = getProducts();

  return (
    <main>
      <Nav />
      <section className="max-w-6xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Featured Products</h1>
          <p className="text-slate-600 mt-1">Live demo catalog for laptops and mobiles (static mode)</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {products.map((p) => (
            <article key={p.id} className="bg-white rounded-xl border shadow-sm overflow-hidden">
              <img src={p.image} alt={p.name} className="w-full h-44 object-cover" />
              <div className="p-4">
                <h2 className="font-semibold text-lg">{p.name}</h2>
                <p className="text-sm text-slate-600 mt-1 line-clamp-2">{p.description}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="font-bold text-blue-700">${p.price}</span>
                  <span className="text-xs bg-slate-100 px-2 py-1 rounded">In stock</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
