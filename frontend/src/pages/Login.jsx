import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { Wordmark } from '../components/TopBar.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Could not sign in')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="center-screen">
      <div className="shell shell-narrow stack reveal" style={{ padding: 0 }}>
        <Wordmark />
        <h1>
          Welcome <em>back.</em>
        </h1>
        <p className="muted">
          Your shared kitchen list, kept in one tidy ledger.
        </p>
        <form className="panel stack" onSubmit={onSubmit}>
          <label className="field">
            <span className="lbl">Email</span>
            <input
              type="email"
              aria-label="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@home.com"
              required
            />
          </label>
          <label className="field">
            <span className="lbl">Password</span>
            <input
              type="password"
              aria-label="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>
          {error && <div role="alert">{error}</div>}
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="muted">
          New here?{' '}
          <Link to="/register" className="link-grow">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  )
}
