import { FormEvent, useEffect, useState } from "react";
import QRCode from "qrcode";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, isAuthError } from "../shared/api";
import { useSessionStore } from "../shared/store";
import type { DiningTable } from "../shared/types";

export default function TableManager() {
  const queryClient = useQueryClient();
  const clearSession = useSessionStore((state) => state.clearSession);
  const [tableCode, setTableCode] = useState("");
  const [label, setLabel] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);

  const tables = useQuery({
    queryKey: ["admin-tables"],
    queryFn: () => api.get<{ tables: DiningTable[] }>("/admin/tables"),
  });

  useEffect(() => {
    if (isAuthError(tables.error)) clearSession();
  }, [clearSession, tables.error]);

  const create = useMutation({
    mutationFn: () => api.post<DiningTable>("/admin/tables", { table_code: tableCode, label }),
    onSuccess: () => {
      setTableCode("");
      setLabel("");
      queryClient.invalidateQueries({ queryKey: ["admin-tables"] });
    },
  });

  const patch = useMutation({
    mutationFn: ({ id, active, label }: { id: number; active?: boolean; label?: string }) =>
      api.patch<DiningTable>(`/admin/tables/${id}`, { ...(active === undefined ? {} : { active }), ...(label ? { label } : {}) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-tables"] }),
  });

  async function showQr(code: string) {
    const url = `${window.location.origin}/t/${encodeURIComponent(code)}/menu`;
    setQrDataUrl(await QRCode.toDataURL(url, { margin: 2, width: 220 }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (tableCode.trim() && label.trim() && !create.isPending) create.mutate();
  }

  return (
    <section className="mx-auto max-w-6xl px-4 py-6">
      <h1 className="text-2xl font-bold text-sf-dark">Tables</h1>
      {tables.error ? (
        <div className="mt-4 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">
          {tables.error instanceof Error ? tables.error.message : "Tables did not load."}
        </div>
      ) : null}
      <form className="mt-5 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={submit}>
        <input className="h-11 rounded-md border border-slate-200 px-3" value={tableCode} onChange={(event) => setTableCode(event.target.value)} placeholder="T-05" />
        <input className="h-11 rounded-md border border-slate-200 px-3" value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Table 5" />
        <button className="rounded-md bg-sf-green px-5 font-bold text-white disabled:bg-slate-300" disabled={create.isPending || !tableCode.trim() || !label.trim()}>
          {create.isPending ? "Creating..." : "Create"}
        </button>
      </form>
      {qrDataUrl ? (
        <div className="mt-5 inline-block rounded-lg border border-slate-200 bg-white p-4">
          <img src={qrDataUrl} alt="QR" className="h-56 w-56" />
        </div>
      ) : null}
      <div className="mt-5 space-y-3">
        {tables.isLoading ? <p className="text-sm text-slate-500">Loading tables...</p> : null}
        {!tables.isLoading && tables.data?.tables.length === 0 ? (
          <p className="rounded-lg border border-slate-200 bg-white p-5 text-center text-sm text-slate-500">No tables yet.</p>
        ) : null}
        {tables.data?.tables.map((table) => (
          <div key={table.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4">
            <div>
              <p className="font-bold text-sf-dark">{table.label}</p>
              <p className="text-sm text-slate-500">{table.table_code} · {table.active ? "Active" : "Inactive"}</p>
            </div>
            <div className="flex gap-2">
              <button className="rounded-md border border-slate-200 px-3 py-2 text-sm" onClick={() => showQr(table.table_code)}>QR</button>
              <button
                className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:opacity-50"
                onClick={() => {
                  const nextLabel = window.prompt("New table label", table.label);
                  if (nextLabel?.trim()) patch.mutate({ id: table.id, label: nextLabel.trim() });
                }}
                disabled={patch.isPending}
              >
                Rename
              </button>
              <button className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:opacity-50" onClick={() => patch.mutate({ id: table.id, active: !table.active })} disabled={patch.isPending}>Toggle</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
