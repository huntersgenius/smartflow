import { useState, type FormEvent } from 'react'
import { api, ApiError } from './shared/api'
import type { StaffLoginResponse, StaffRole } from './shared/types'

interface LoginPageProps {
  role: StaffRole
  onSuccess: (data: StaffLoginResponse) => void
}

export default function LoginPage({ role, onSuccess }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isAdmin = role === 'admin'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!email || !password) return

    setLoading(true)
    setError(null)

    try {
      const data = await api.post<StaffLoginResponse>('/auth/staff/login', { email, password })
      if (isAdmin ? data.role !== 'admin' : !['kitchen', 'admin'].includes(data.role)) {
        void api.post('/auth/staff/logout', {}).catch(() => undefined)
        setError(isAdmin ? 'Admin access is required.' : 'Kitchen access is required.')
        setLoading(false)
        return
      }
      onSuccess(data)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-terminal-bg flex items-center justify-center p-6 font-barlow">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-full bg-gradient-to-b from-blue-500/20 via-transparent to-transparent" />
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="absolute text-terminal-border font-mono text-xs opacity-20 select-none"
            style={{
              top: `${15 + i * 14}%`,
              left: `${8 + (i % 2) * 72}%`,
              animationDelay: `${i * 0.5}s`,
            }}
          >
            {['ORDER:PENDING', 'STATUS:READY', isAdmin ? 'ADMIN:ONLINE' : 'KITCHEN:ONLINE', 'QUEUE:03', 'BRANCH:01', 'STAFF:AUTH'][i]}
          </div>
        ))}
      </div>

      <div className="relative w-full max-w-sm animate-scale-in">
        {/* Logo area */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 mb-5">
            <span className="text-3xl">{isAdmin ? 'SF' : '👨‍🍳'}</span>
          </div>
          <h1 className="font-barlow text-3xl font-bold text-terminal-text tracking-wider uppercase">
            SmartFlow
          </h1>
          <p className="text-terminal-muted text-sm mt-1 tracking-widest uppercase font-medium">
            {isAdmin ? 'Admin Station' : 'Kitchen Station'}
          </p>
        </div>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          className="bg-terminal-card border border-terminal-border rounded-2xl p-8 space-y-5 shadow-2xl"
        >
          <div>
            <label className="block text-terminal-muted text-xs font-medium tracking-widest uppercase mb-2">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="staff@restaurant.com"
              required
              className="w-full bg-terminal-bg border border-terminal-border hover:border-blue-500/30 focus:border-blue-500/60 rounded-lg px-4 py-3 text-terminal-text text-sm placeholder:text-terminal-muted/40 outline-none transition-colors focus:ring-1 focus:ring-blue-500/20"
            />
          </div>

          <div>
            <label className="block text-terminal-muted text-xs font-medium tracking-widest uppercase mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full bg-terminal-bg border border-terminal-border hover:border-blue-500/30 focus:border-blue-500/60 rounded-lg px-4 py-3 text-terminal-text text-sm placeholder:text-terminal-muted/40 outline-none transition-colors focus:ring-1 focus:ring-blue-500/20"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm animate-slide-down">
              <span>⚠</span>
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full py-3.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg font-barlow font-bold text-white tracking-widest uppercase text-sm transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Authenticating…</span>
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <p className="text-center text-terminal-muted/40 text-xs mt-6 tracking-wider">
          SMARTFLOW KITCHEN SYSTEM v1.0
        </p>
      </div>
    </div>
  )
}
