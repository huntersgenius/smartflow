import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import GuestApp from './guest/GuestApp'
import KitchenApp from './kitchen/KitchenApp'
import AdminApp from './admin/AdminApp'

const KitchenLoginPage = lazy(() => import('./kitchen/LoginPage'))
const OrderBoard = lazy(() => import('./kitchen/OrderBoard'))
const AdminLoginPage = lazy(() => import('./admin/LoginPage'))
const MenuManager = lazy(() => import('./admin/MenuManager'))
const CategoryManager = lazy(() => import('./admin/CategoryManager'))
const TableManager = lazy(() => import('./admin/TableManager'))
const OrderHistory = lazy(() => import('./admin/OrderHistory'))

export default function App() {
  return (
    <Suspense fallback={<AppLoader />}>
      <Routes>
        {/* Guest ordering flow */}
        <Route path="/t/:tableCode/*" element={<GuestApp />} />

        {/* Kitchen staff panel */}
        <Route path="/kitchen" element={<KitchenApp />}>
          <Route index element={<Navigate to="/kitchen/login" replace />} />
          <Route path="login" element={<KitchenLoginPage />} />
          <Route path="board" element={<OrderBoard />} />
        </Route>

        {/* Admin panel */}
        <Route path="/admin" element={<AdminApp />}>
          <Route index element={<Navigate to="/admin/login" replace />} />
          <Route path="login" element={<AdminLoginPage />} />
          <Route path="menu" element={<MenuManager />} />
          <Route path="categories" element={<CategoryManager />} />
          <Route path="tables" element={<TableManager />} />
          <Route path="orders" element={<OrderHistory />} />
        </Route>

        {/* Default redirect */}
        <Route
          path="/"
          element={
            <div className="min-h-screen bg-ember-900 flex items-center justify-center font-outfit text-ember-100">
              <div className="text-center animate-fade-in">
                <div className="text-6xl mb-6">🍽️</div>
                <h1 className="font-fraunces text-4xl font-light mb-2">SmartFlow</h1>
                <p className="text-ember-400 text-sm">Restaurant QR Ordering</p>
                <div className="mt-10 flex gap-4 justify-center text-sm">
                  <a
                    href="/kitchen/login"
                    className="px-5 py-2.5 bg-ember-500/20 hover:bg-ember-500/30 border border-ember-500/30 rounded-lg transition-colors"
                  >
                    Kitchen Panel
                  </a>
                  <a
                    href="/admin/login"
                    className="px-5 py-2.5 bg-ember-500/20 hover:bg-ember-500/30 border border-ember-500/30 rounded-lg transition-colors"
                  >
                    Admin Panel
                  </a>
                </div>
              </div>
            </div>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

function AppLoader() {
  return (
    <div className="phone-shell grid place-items-center">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-sf-mint border-t-sf-green" />
    </div>
  )
}
