import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext.jsx'
import { Wordmark } from '../components/TopBar.jsx'

export default function Register() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api('/auth/register', {
        method: 'POST',
        body: { email, password, display_name: name },
        auth: false,
      })
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Could not create account')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="center-screen">
      <div className="shell shell-narrow stack reveal" style={{ padding: 0 }}>
        <Wordmark />
        <h1>
          Start your <em>ledger.</em>
        </h1>
        <p className="muted">One household, one list, everyone in sync.</p>
        <form className="panel stack" onSubmit={onSubmit}>
          <label className="field">
            <span className="lbl">Name</span>
            <input
              type="text"
              aria-label="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tal Levi"
              required
            />
          </label>
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
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>
          {error && <div role="alert">{error}</div>}
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? 'Creating…' : 'Create account'}
          </button>
        </form>
        <p className="muted">
          Already have an account?{' '}
          <Link to="/login" className="link-grow">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  )
}
