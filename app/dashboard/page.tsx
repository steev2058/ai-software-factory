import Nav from '../../components/Nav';

export default function DashboardPage() {
  return (
    <main>
      <Nav />
      <section className="p-6">
        <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border p-4">Orders Today: 12</div>
          <div className="bg-white rounded-xl border p-4">Revenue: $1,240</div>
          <div className="bg-white rounded-xl border p-4">Pending: 4</div>
        </div>
      </section>
    </main>
  );
}
