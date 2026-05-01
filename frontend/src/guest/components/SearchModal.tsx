import { X } from "lucide-react";
import { money } from "../../shared/format";
import type { MenuCategory } from "../../shared/types";

interface SearchModalProps {
  open: boolean;
  query: string;
  categories: MenuCategory[];
  onQuery: (value: string) => void;
  onClose: () => void;
  onPickCategory: (categoryId: number) => void;
}

export default function SearchModal({ open, query, categories, onQuery, onClose, onPickCategory }: SearchModalProps) {
  if (!open) return null;
  const trimmedQuery = query.trim().toLowerCase();
  const results = categories
    .flatMap((category) => category.items.map((item) => ({ ...item, categoryId: category.id, categoryName: category.name })))
    .filter((item) => trimmedQuery.length > 0 && item.name.toLowerCase().includes(trimmedQuery))
    .slice(0, 8);

  return (
    <div className="fixed inset-0 z-50 mx-auto max-w-[430px] bg-white p-4">
      <div className="flex items-center gap-2">
        <input
          autoFocus
          value={query}
          onChange={(event) => onQuery(event.target.value)}
          placeholder="Taom qidirish"
          className="h-11 flex-1 rounded-lg border border-sf-line px-4 outline-none focus:border-sf-green"
        />
        <button className="grid h-11 w-11 place-items-center rounded-lg bg-sf-mint text-sf-dark" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      <div className="mt-4 space-y-2">
        {trimmedQuery.length === 0 ? (
          <p className="rounded-lg bg-sf-mint p-4 text-sm text-slate-600">Taom nomini yozing.</p>
        ) : null}
        {trimmedQuery.length > 0 && results.length === 0 ? (
          <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Hech narsa topilmadi.</p>
        ) : null}
        {results.map((item) => (
          <button
            key={item.id}
            className="block w-full rounded-lg border border-sf-line p-3 text-left"
            onClick={() => onPickCategory(item.categoryId)}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-sf-dark">{item.name}</p>
                <p className="text-sm text-slate-500">{item.categoryName}</p>
              </div>
              <span className="text-sm font-bold text-sf-green">{money(item.price)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
