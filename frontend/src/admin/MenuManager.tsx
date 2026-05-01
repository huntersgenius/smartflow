import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, isAuthError } from "../shared/api";
import { money } from "../shared/format";
import { useSessionStore } from "../shared/store";
import type { AdminCategory, AdminMenuItem } from "../shared/types";

export default function MenuManager() {
  const queryClient = useQueryClient();
  const clearSession = useSessionStore((state) => state.clearSession);
  const [categoryId, setCategoryId] = useState<number>(1);
  const [name, setName] = useState("");
  const [price, setPrice] = useState("10000.00");

  const categories = useQuery({
    queryKey: ["admin-categories"],
    queryFn: () => api.get<{ categories: AdminCategory[] }>("/admin/categories"),
  });
  const items = useQuery({
    queryKey: ["admin-menu-items"],
    queryFn: () => api.get<{ items: AdminMenuItem[] }>("/admin/menu-items"),
  });

  const activeCategories = useMemo(() => categories.data?.categories.filter((category) => category.active) ?? [], [categories.data]);
  const validPrice = Number.isFinite(Number(price)) && Number(price) >= 0;
  const loadError = categories.error || items.error;

  useEffect(() => {
    if (activeCategories.length > 0 && !activeCategories.some((category) => category.id === categoryId)) {
      setCategoryId(activeCategories[0].id);
    }
  }, [activeCategories, categoryId]);

  useEffect(() => {
    if (isAuthError(categories.error) || isAuthError(items.error)) clearSession();
  }, [categories.error, clearSession, items.error]);

  const create = useMutation({
    mutationFn: () => api.post<AdminMenuItem>("/admin/menu-items", { category_id: categoryId, name, price }),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["admin-menu-items"] });
      queryClient.invalidateQueries({ queryKey: ["menu"] });
    },
  });

  const patch = useMutation({
    mutationFn: ({ id, available, price }: { id: string; available?: boolean; price?: string }) =>
      api.patch<AdminMenuItem>(`/admin/menu-items/${id}`, { ...(available === undefined ? {} : { available }), ...(price ? { price } : {}) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-menu-items"] });
      queryClient.invalidateQueries({ queryKey: ["menu"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete<{ message: string }>(`/admin/menu-items/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-menu-items"] });
      queryClient.invalidateQueries({ queryKey: ["menu"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (name.trim() && activeCategories.length > 0 && validPrice && !create.isPending) create.mutate();
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-6">
      <h1 className="text-2xl font-bold text-sf-dark">Menu Manager</h1>
      {loadError ? (
        <div className="mt-4 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">
          {loadError instanceof Error ? loadError.message : "Ma'lumot yuklanmadi."}
        </div>
      ) : null}
      <form className="mt-5 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-[1fr_2fr_1fr_auto]" onSubmit={submit}>
        <select className="h-11 rounded-md border border-slate-200 px-3 disabled:bg-slate-50" value={categoryId} onChange={(event) => setCategoryId(Number(event.target.value))} disabled={activeCategories.length === 0}>
          {activeCategories.length === 0 ? <option>Kategoriya yo'q</option> : null}
          {activeCategories.map((category) => (
            <option key={category.id} value={category.id}>{category.name}</option>
          ))}
        </select>
        <input className="h-11 rounded-md border border-slate-200 px-3" value={name} onChange={(event) => setName(event.target.value)} placeholder="Item name" />
        <input className="h-11 rounded-md border border-slate-200 px-3" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="Price" />
        <button className="rounded-md bg-sf-green px-5 font-bold text-white disabled:bg-slate-300" disabled={create.isPending || !name.trim() || activeCategories.length === 0 || !validPrice}>
          {create.isPending ? "Creating..." : "Create"}
        </button>
      </form>

      <div className="admin-grid mt-5">
        {items.isLoading ? <p className="text-sm text-slate-500">Loading items...</p> : null}
        {!items.isLoading && items.data?.items.length === 0 ? (
          <p className="rounded-lg border border-slate-200 bg-white p-5 text-center text-sm text-slate-500">No menu items yet.</p>
        ) : null}
        {items.data?.items.map((item) => (
          <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-sf-green">{item.category_name}</p>
                <h2 className="mt-1 font-bold text-sf-dark">{item.name}</h2>
                <p className="mt-1 text-sm text-slate-500">{money(item.price)}</p>
              </div>
              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.available ? "bg-sf-mint text-sf-green" : "bg-slate-100 text-slate-500"}`}>
                {item.available ? "Available" : "Off"}
              </span>
            </div>
            <div className="mt-4 flex gap-2">
              <button className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:opacity-50" onClick={() => patch.mutate({ id: item.id, available: !item.available })} disabled={patch.isPending || remove.isPending}>
                Toggle
              </button>
              <button className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:opacity-50" onClick={() => patch.mutate({ id: item.id, price: String(Number(item.price) + 1000) })} disabled={patch.isPending || remove.isPending}>
                +1000
              </button>
              <button
                className="rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 disabled:opacity-50"
                onClick={() => {
                  if (window.confirm("Delete this item?")) remove.mutate(item.id);
                }}
                disabled={patch.isPending || remove.isPending}
              >
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
