import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useSessionStore } from "../shared/store";

const links = [
  { to: "/admin/menu", label: "Menu" },
  { to: "/admin/categories", label: "Categories" },
  { to: "/admin/tables", label: "Tables" },
  { to: "/admin/orders", label: "Orders" },
];

export default function AdminApp() {
  const location = useLocation();
  const isLogin = location.pathname === "/admin/login";
  const role = useSessionStore((state) => state.role);

  if (!isLogin && role !== "admin") {
    return <Navigate to="/admin/login" replace />;
  }

  return (
    <main className="min-h-screen bg-slate-50">
      {!isLogin ? (
        <header className="border-b border-slate-200 bg-white px-5 py-3">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-lg font-bold text-sf-dark">SmartFlow Admin</p>
              <p className="text-xs text-slate-500">Menyu, stollar va buyurtmalar</p>
            </div>
            <nav className="flex flex-wrap gap-2 text-sm font-semibold">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  className={({ isActive }) => `rounded-md px-3 py-2 ${isActive ? "bg-sf-green text-white" : "hover:bg-sf-mint"}`}
                  to={link.to}
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>
      ) : null}
      <Outlet />
    </main>
  );
}
