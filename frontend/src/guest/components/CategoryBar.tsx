interface CategoryBarProps {
  categories: Array<{ id: number; name: string; itemCount: number }>;
  activeId: number;
  onSelect: (id: number) => void;
}

export default function CategoryBar({ categories, activeId, onSelect }: CategoryBarProps) {
  const all = [{ id: -1, name: "Barchasi", itemCount: 0 }, ...categories];

  return (
    <div className="sticky top-0 z-20 border-b border-sf-line bg-white/95 px-4 py-3 backdrop-blur">
      <div className="hide-scrollbar flex gap-2 overflow-x-auto">
        {all.map((category) => {
          const isActive = activeId === category.id || (category.id === -1 && activeId === 0);
          return (
            <button
              key={`${category.id}-${category.name}`}
              className={`shrink-0 rounded-full border px-4 py-2 text-sm font-semibold transition ${
                isActive
                  ? "border-sf-green bg-sf-green text-white"
                  : "border-sf-line bg-white text-sf-dark"
              }`}
              onClick={() => onSelect(category.id)}
            >
              {category.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
