import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useSessionStore } from "../shared/store";

export default function KitchenApp() {
  const location = useLocation();
  const isLogin = location.pathname === "/kitchen/login";
  const role = useSessionStore((state) => state.role);
  return (
    <main className="min-h-screen bg-slate-50">
      {!isLogin ? (
        <header className="no-print border-b border-slate-200 bg-white px-5 py-3">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <div>
              <p className="text-lg font-bold text-sf-dark">SmartFlow Kitchen</p>
              <p className="text-xs text-slate-500">{role ? `Rol: ${role}` : "Oshxona paneli"}</p>
            </div>
            <nav className="flex gap-2 text-sm font-semibold">
              <NavLink className="rounded-md px-3 py-2 hover:bg-sf-mint" to="/kitchen/login">Login</NavLink>
              <NavLink className="rounded-md px-3 py-2 hover:bg-sf-mint" to="/kitchen/board">Board</NavLink>
            </nav>
          </div>
        </header>
      ) : null}
      <Outlet />
    </main>
  );
}
