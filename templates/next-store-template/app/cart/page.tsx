import Nav from '../../components/Nav';
import { getProducts } from '../../lib/demoData';

export default function CartPage() {
  const items = getProducts().slice(0, 2);
  const subtotal = items.reduce((sum, i) => sum + i.price, 0);

  return (
    <main>
      <Nav />
      <section className="max-w-5xl mx-auto p-6 space-y-4">
        <h1 className="text-3xl font-bold">Your Cart</h1>
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="bg-white border rounded-xl p-4 flex items-center gap-4">
              <img src={item.image} alt={item.name} className="w-20 h-20 rounded object-cover" />
              <div className="flex-1">
                <h2 className="font-semibold">{item.name}</h2>
                <p className="text-sm text-slate-500">Qty: 1</p>
              </div>
              <div className="font-bold">${item.price}</div>
            </div>
          ))}
        </div>

        <div className="bg-white border rounded-xl p-4 flex items-center justify-between">
          <div className="text-slate-600">Subtotal</div>
          <div className="text-xl font-bold text-blue-700">${subtotal}</div>
        </div>
      </section>
    </main>
  );
}
