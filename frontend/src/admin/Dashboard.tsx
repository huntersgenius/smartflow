export default function Dashboard() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-6">
      <h1 className="text-2xl font-bold text-sf-dark">Dashboard</h1>
      <div className="admin-grid mt-5">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">Bugungi buyurtmalar</p>
          <p className="mt-2 text-3xl font-bold text-sf-dark">0</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">Faol menyu</p>
          <p className="mt-2 text-3xl font-bold text-sf-dark">Online</p>
        </div>
      </div>
    </section>
  );
}
