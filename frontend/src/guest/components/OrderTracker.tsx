import type { OrderStatus } from "../../shared/types";

const steps: Array<{ key: OrderStatus; label: string }> = [
  { key: "pending", label: "Yuborildi" },
  { key: "accepted", label: "Qabul qilindi" },
  { key: "preparing", label: "Tayyorlanmoqda" },
  { key: "ready", label: "Tayyor" },
];

export default function OrderTracker({ status }: { status: OrderStatus | null }) {
  if (status === "cancelled") {
    return (
      <div className="rounded-lg border border-red-100 bg-red-50 p-4">
        <p className="font-semibold text-red-700">Buyurtma bekor qilindi</p>
        <p className="mt-1 text-sm text-red-600">Iltimos, ofitsiantga murojaat qiling.</p>
      </div>
    );
  }

  const activeIndex = status === "served" ? steps.length - 1 : Math.max(0, steps.findIndex((step) => step.key === status));
  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step.key} className="flex items-center gap-3">
          <div className={`grid h-8 w-8 place-items-center rounded-full text-sm font-bold ${
            index <= activeIndex ? "bg-sf-green text-white" : "bg-slate-100 text-slate-400"
          }`}>
            {index + 1}
          </div>
          <span className={`font-semibold ${index <= activeIndex ? "text-sf-dark" : "text-slate-400"}`}>{step.label}</span>
        </div>
      ))}
    </div>
  );
}
