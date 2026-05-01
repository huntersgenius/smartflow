export default function DailySpecialBanner() {
  return (
    <section className="mx-4 rounded-lg border border-sf-line bg-sf-mint p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-sf-green">Bugungi taklif</p>
          <h2 className="mt-1 text-lg font-bold text-sf-dark">Burger + ichimlik -10%</h2>
          <p className="mt-1 text-sm text-slate-600">Savatga ichimlik qo'shsangiz chegirma kassada hisoblanadi.</p>
        </div>
        <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-white text-sm font-bold text-sf-green shadow-sm">
          -10%
        </div>
      </div>
    </section>
  );
}
