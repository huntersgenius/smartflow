import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

const AdminApp = lazy(() => import("./admin/AdminApp"));
const CategoryManager = lazy(() => import("./admin/CategoryManager"));
const AdminLoginPage = lazy(() => import("./admin/LoginPage"));
const MenuManager = lazy(() => import("./admin/MenuManager"));
const OrderHistory = lazy(() => import("./admin/OrderHistory"));
const TableManager = lazy(() => import("./admin/TableManager"));
const CartPage = lazy(() => import("./guest/CartPage"));
const GuestApp = lazy(() => import("./guest/GuestApp"));
const MenuPage = lazy(() => import("./guest/MenuPage"));
const OrderStatusPage = lazy(() => import("./guest/OrderStatusPage"));
const KitchenApp = lazy(() => import("./kitchen/KitchenApp"));
const KitchenLoginPage = lazy(() => import("./kitchen/LoginPage"));
const OrderBoard = lazy(() => import("./kitchen/OrderBoard"));

export default function App() {
  return (
    <Suspense fallback={<AppLoader />}>
      <Routes>
        <Route path="/" element={<Navigate to="/t/T-12-B/menu" replace />} />

        <Route path="/t/:tableCode" element={<GuestApp />}>
          <Route index element={<Navigate to="menu" replace />} />
          <Route path="menu" element={<MenuPage />} />
          <Route path="cart" element={<CartPage />} />
          <Route path="order/:orderId" element={<OrderStatusPage />} />
        </Route>

        <Route path="/kitchen" element={<KitchenApp />}>
          <Route index element={<Navigate to="/kitchen/login" replace />} />
          <Route path="login" element={<KitchenLoginPage />} />
          <Route path="board" element={<OrderBoard />} />
        </Route>

        <Route path="/admin" element={<AdminApp />}>
          <Route index element={<Navigate to="/admin/login" replace />} />
          <Route path="login" element={<AdminLoginPage />} />
          <Route path="menu" element={<MenuManager />} />
          <Route path="categories" element={<CategoryManager />} />
          <Route path="tables" element={<TableManager />} />
          <Route path="orders" element={<OrderHistory />} />
        </Route>

        <Route path="*" element={<Navigate to="/t/T-12-B/menu" replace />} />
      </Routes>
    </Suspense>
  );
}

function AppLoader() {
  return (
    <div className="phone-shell grid place-items-center">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-sf-mint border-t-sf-green" />
    </div>
  );
}
