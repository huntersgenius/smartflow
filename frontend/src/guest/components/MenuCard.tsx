import { Minus, Plus } from "lucide-react";

import { displayCategoryName, fallbackFoodImage, money, productMeta, usableImageUrl } from "../../shared/format";
import type { CartItem, MenuCategory, MenuItem } from "../../shared/types";
import LazyImage from "../../shared/components/LazyImage";

interface MenuCardProps {
  item: MenuItem;
  category: MenuCategory;
  quantity: number;
  onAdd: (item: CartItem) => void;
  onRemove: () => void;
}

export default function MenuCard({ item, category, quantity, onAdd, onRemove }: MenuCardProps) {
  const meta = productMeta(item);
  const available = item.available;
  const cartItem: CartItem = {
    ...item,
    quantity,
    cookTimeMin: meta.cookTimeMin,
    calories: meta.calories,
    categoryName: displayCategoryName(category.name),
  };

  return (
    <article
      className={`snap-card flex min-h-[238px] flex-col rounded-lg border border-sf-line bg-white p-2 shadow-sm transition ${
        available ? "" : "opacity-50 grayscale"
      }`}
    >
      <LazyImage
        src={usableImageUrl(item.thumbnail_url || item.image_url)}
        alt={item.name}
        fallbackClassName="aspect-square rounded-md"
        fallbackStyle={{ background: fallbackFoodImage(item.name) }}
        className="h-full w-full rounded-md object-cover"
      />
      <div className="mt-2 flex flex-1 flex-col">
        <h3 className="line-clamp-2 min-h-[34px] text-[13px] font-semibold leading-tight text-sf-dark">{item.name}</h3>
        <p className="mt-1 text-[12px] font-bold text-sf-green">{money(item.price)}</p>
        <div className="mt-1 space-y-1 text-[10px] leading-tight text-slate-500">
          <p>{meta.cookTimeMin} daq</p>
          <p>{meta.calories} kcal</p>
          <p className={available ? "font-semibold text-sf-green" : "font-semibold text-slate-500"}>
            {available ? "Mavjud" : "Tugagan"}
          </p>
        </div>
        {item.description ? <p className="mt-1 line-clamp-2 text-[10px] leading-tight text-slate-500">{item.description}</p> : null}
        <div className="mt-auto flex items-center justify-between rounded-md bg-sf-mint p-1">
          <button
            className="grid h-7 w-7 place-items-center rounded-md bg-white text-sf-dark disabled:opacity-40"
            onClick={onRemove}
            disabled={quantity === 0}
            aria-label="Kamaytirish"
          >
            <Minus size={14} />
          </button>
          <span className="w-6 text-center text-xs font-bold text-sf-dark">{quantity}</span>
          <button
            className="grid h-7 w-7 place-items-center rounded-md bg-sf-green text-white disabled:bg-slate-200"
            onClick={() => onAdd(cartItem)}
            disabled={!available}
            aria-label="Qo'shish"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>
    </article>
  );
}
