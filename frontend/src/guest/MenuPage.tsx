import { createRef, useMemo, useState, type ComponentProps } from "react";
import { Search, ShoppingBag } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../shared/api";
import { displayCategoryName } from "../shared/format";
import { useCartStore } from "../shared/store";
import type { MenuCategory, MenuResponse } from "../shared/types";
import SkeletonCard from "../shared/components/SkeletonCard";
import CartSheet from "./components/CartSheet";
import CategoryBar from "./components/CategoryBar";
import DailySpecialBanner from "./components/DailySpecialBanner";
import MenuCard from "./components/MenuCard";
import SearchModal from "./components/SearchModal";
import UpsellModal from "./components/UpsellModal";
import { useCategoryScroll } from "./hooks/useCategoryScroll";

export default function MenuPage() {
  const navigate = useNavigate();
  const { tableCode } = useParams();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [upsellOpen, setUpsellOpen] = useState(false);
  const branchId = useCartStore((state) => state.branchId);
  const items = useCartStore((state) => state.items);
  const addItem = useCartStore((state) => state.addItem);
  const updateQty = useCartStore((state) => state.updateQty);
  const itemCount = useCartStore((state) => state.itemCount());

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["menu", branchId],
    queryFn: () => api.get<MenuResponse>(`/menu?branch_id=${branchId}`),
    staleTime: 300_000,
  });

  const categories = data?.categories ?? [];
  const visibleCategories = useMemo(() => categories.filter((category) => category.items.length > 0), [categories]);
  const sectionRefs = useMemo(() => {
    return new Map(visibleCategories.map((category) => [category.id, createRef<HTMLDivElement>()]));
  }, [visibleCategories]);
  const { activeId, setActiveId } = useCategoryScroll(sectionRefs, visibleCategories[0]?.id ?? 0);

  function qty(id: string) {
    return items.find((item) => item.id === id)?.quantity ?? 0;
  }

  function selectCategory(id: number) {
    if (id === -1) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      setActiveId(0);
      return;
    }
    const node = sectionRefs.get(id)?.current;
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
    }
  }

  function handleAdd(item: Parameters<typeof addItem>[0]) {
    addItem(item);
    if (item.categoryName.toLowerCase().includes("burger")) {
      setUpsellOpen(true);
    }
  }

  return (
    <main className="phone-shell relative pb-28">
      <header className="px-4 pb-3 pt-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-lg font-bold text-sf-dark">Stol #{tableCode}</p>
            <p className="mt-1 text-sm text-slate-500">Xush kelibsiz! Menyudan tanlang.</p>
          </div>
          <div className="flex gap-2">
            <button className="grid h-10 w-10 place-items-center rounded-full bg-sf-mint text-sf-dark" onClick={() => setSearchOpen(true)}>
              <Search size={19} />
            </button>
            <button className="relative grid h-10 w-10 place-items-center rounded-full bg-sf-green text-white" onClick={() => navigate(`/t/${tableCode}/cart`)}>
              <ShoppingBag size={19} />
              {itemCount > 0 ? (
                <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-sf-dark px-1 text-[10px] font-bold">
                  {itemCount}
                </span>
              ) : null}
            </button>
          </div>
        </div>
      </header>

      <CategoryBar
        categories={visibleCategories.map((category) => ({
          id: category.id,
          name: displayCategoryName(category.name),
          itemCount: category.items.length,
        }))}
        activeId={activeId}
        onSelect={selectCategory}
      />

      {isLoading ? (
        <section className="space-y-6 px-4 pt-5">
          <div className="snap-row">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </section>
      ) : error ? (
        <section className="px-4 pt-8 text-center">
          <div className="rounded-lg border border-red-100 bg-red-50 p-5">
            <p className="font-semibold text-red-700">Menyu yuklanmadi</p>
            <p className="mt-2 text-sm text-red-600">{error instanceof Error ? error.message : "Qayta urinib ko'ring."}</p>
            <button
              className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
              onClick={() => void refetch()}
              disabled={isFetching}
            >
              {isFetching ? "Yuklanmoqda..." : "Qayta urinish"}
            </button>
          </div>
        </section>
      ) : visibleCategories.length === 0 ? (
        <section className="px-4 pt-8 text-center">
          <div className="rounded-lg border border-sf-line bg-sf-mint p-5">
            <p className="font-semibold text-sf-dark">Hozircha menyuda mahsulot yo'q</p>
            <p className="mt-2 text-sm text-slate-500">Iltimos, ofitsiantga murojaat qiling.</p>
          </div>
        </section>
      ) : (
        <div className="space-y-7 pt-5">
          <MenuSection
            title="Siz uchun tavsiya"
            category={visibleCategories[0]}
            items={visibleCategories.flatMap((category) => category.items).slice(0, 6)}
            quantity={qty}
            onAdd={handleAdd}
            onRemove={(id) => updateQty(id, qty(id) - 1)}
          />
          <DailySpecialBanner />
          {visibleCategories.map((category) => (
            <div key={category.id} ref={sectionRefs.get(category.id)} data-category-id={category.id}>
              <MenuSection
                title={displayCategoryName(category.name)}
                category={category}
                items={category.items}
                quantity={qty}
                onAdd={handleAdd}
                onRemove={(id) => updateQty(id, qty(id) - 1)}
              />
            </div>
          ))}
        </div>
      )}

      <CartSheet />
      <SearchModal
        open={searchOpen}
        query={query}
        categories={visibleCategories}
        onQuery={setQuery}
        onClose={() => setSearchOpen(false)}
        onPickCategory={(categoryId) => {
          setSearchOpen(false);
          selectCategory(categoryId);
        }}
      />
      <UpsellModal open={upsellOpen} onClose={() => setUpsellOpen(false)} />
    </main>
  );
}

interface MenuSectionProps {
  title: string;
  category?: MenuCategory;
  items: MenuCategory["items"];
  quantity: (id: string) => number;
  onAdd: ComponentProps<typeof MenuCard>["onAdd"];
  onRemove: (id: string) => void;
}

function MenuSection({ title, category, items, quantity, onAdd, onRemove }: MenuSectionProps) {
  if (items.length === 0) return null;
  const sectionCategory = category ?? {
    id: 0,
    name: title,
    description: null,
    image_url: null,
    sort_order: 0,
    items,
  };

  return (
    <section className="px-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-bold text-sf-dark">{title}</h2>
        <span className="text-sm font-semibold text-sf-green">Ko'rish &rarr;</span>
      </div>
      <div className="relative">
        <div className="snap-row pb-1">
          {items.map((item) => (
            <MenuCard
              key={item.id}
              item={item}
              category={sectionCategory}
              quantity={quantity(item.id)}
              onAdd={onAdd}
              onRemove={() => onRemove(item.id)}
            />
          ))}
        </div>
        {items.length > 3 ? (
          <div className="pointer-events-none absolute right-0 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full bg-white/95 text-sf-green shadow">
            &rarr;
          </div>
        ) : null}
      </div>
    </section>
  );
}
