import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, isAuthError } from "../shared/api";
import { useSessionStore } from "../shared/store";
import type { AdminCategory } from "../shared/types";

export default function CategoryManager() {
  const queryClient = useQueryClient();
  const clearSession = useSessionStore((state) => state.clearSession);
  const [name, setName] = useState("");

  const categories = useQuery({
    queryKey: ["admin-categories"],
    queryFn: () => api.get<{ categories: AdminCategory[] }>("/admin/categories"),
  });

  useEffect(() => {
    if (isAuthError(categories.error)) clearSession();
  }, [categories.error, clearSession]);

  const create = useMutation({
    mutationFn: () => api.post<AdminCategory>("/admin/categories", { name, sort_order: categories.data?.categories.length ?? 0 }),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] });
      queryClient.invalidateQueries({ queryKey: ["menu"] });
    },
  });

  const patch = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => api.patch<AdminCategory>(`/admin/categories/${id}`, { active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] });
      queryClient.invalidateQueries({ queryKey: ["menu"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete<{ message: string }>(`/admin/categories/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] });
      queryClient.invalidateQueries({ queryKey: ["menu"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (name.trim() && !create.isPending) create.mutate();
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-6">
      <h1 className="text-2xl font-bold text-sf-dark">Categories</h1>
      {categories.error ? (
        <div className="mt-4 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">
          {categories.error instanceof Error ? categories.error.message : "Categories did not load."}
        </div>
      ) : null}
      <form className="mt-5 flex gap-2 rounded-lg border border-slate-200 bg-white p-4" onSubmit={submit}>
        <input className="h-11 flex-1 rounded-md border border-slate-200 px-3" value={name} onChange={(event) => setName(event.target.value)} placeholder="Category name" />
        <button className="rounded-md bg-sf-green px-5 font-bold text-white disabled:bg-slate-300" disabled={create.isPending || !name.trim()}>
          {create.isPending ? "Creating..." : "Create"}
        </button>
      </form>
      <div className="mt-5 space-y-3">
        {categories.isLoading ? <p className="text-sm text-slate-500">Loading categories...</p> : null}
        {!categories.isLoading && categories.data?.categories.length === 0 ? (
          <p className="rounded-lg border border-slate-200 bg-white p-5 text-center text-sm text-slate-500">No categories yet.</p>
        ) : null}
        {categories.data?.categories.map((category) => (
          <div key={category.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4">
            <div>
              <p className="font-semibold text-sf-dark">{category.name}</p>
              <p className="text-sm text-slate-500">{category.active ? "Active" : "Inactive"}</p>
            </div>
            <div className="flex gap-2">
              <button className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:opacity-50" onClick={() => patch.mutate({ id: category.id, active: !category.active })} disabled={patch.isPending || remove.isPending}>
                Toggle
              </button>
              <button
                className="rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 disabled:opacity-50"
                onClick={() => {
                  if (window.confirm("Delete this category?")) remove.mutate(category.id);
                }}
                disabled={patch.isPending || remove.isPending}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
