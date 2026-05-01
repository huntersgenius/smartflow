interface UpsellModalProps {
  open: boolean;
  onClose: () => void;
}

export default function UpsellModal({ open, onClose }: UpsellModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-black/30">
      <div className="w-full max-w-[430px] rounded-t-2xl bg-white p-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-sf-green">Taklif</p>
        <h2 className="mt-1 text-xl font-bold text-sf-dark">Ichimlik ham qo'shasizmi?</h2>
        <p className="mt-2 text-sm text-slate-600">Burger bilan ichimlik buyurtma qilsangiz kutish vaqti deyarli o'zgarmaydi.</p>
        <button className="mt-4 w-full rounded-lg bg-sf-green py-3 font-bold text-white" onClick={onClose}>
          Davom etish
        </button>
      </div>
    </div>
  );
}
