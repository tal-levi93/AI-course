import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, getToken } from '../api/client'
import { useAuth } from '../auth/AuthContext.jsx'
import TopBar from '../components/TopBar.jsx'

export default function AcceptInvite() {
  const { ready } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  // working | needauth | error | manual
  const [status, setStatus] = useState('working')
  const [error, setError] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!ready) return
    let active = true

    if (!getToken()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- route decision on mount
      setStatus('needauth')
      return
    }

    // No token in the URL: let a logged-in user paste an invite code.
    if (!token) {
      setStatus('manual')
      return
    }

    ;(async () => {
      try {
        const res = await api('/invitations/accept', {
          method: 'POST',
          body: { token },
        })
        if (!active) return
        navigate(`/households/${res.household_id}`)
      } catch (err) {
        if (!active) return
        setError(err.message || 'Could not accept invitation')
        setStatus('error')
      }
    })()

    return () => {
      active = false
    }
  }, [ready, token, navigate])

  async function acceptCode(e) {
    e.preventDefault()
    if (!code.trim()) return
    setError('')
    setBusy(true)
    try {
      const res = await api('/invitations/accept', {
        method: 'POST',
        body: { token: code.trim() },
      })
      navigate(`/households/${res.household_id}`)
    } catch (err) {
      setError(err.message || 'Could not accept invitation')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <TopBar />
      <main className="shell shell-narrow stack reveal">
        <p className="eyebrow">Invitation</p>
        <h1>
          Join the <em>household.</em>
        </h1>

        {status === 'working' && (
          <div className="panel">
            <p className="muted mono">Accepting your invitation…</p>
          </div>
        )}

        {status === 'manual' && (
          <div className="panel stack">
            <p className="muted">
              Have an invite code? Paste it below to join the household. You
              must be signed in with the <b>invited email address</b>.
            </p>
            <hr className="divider" />
            <form className="row wrap" onSubmit={acceptCode}>
              <input
                className="grow mono"
                type="text"
                aria-label="invite code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Paste invite code"
              />
              <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? 'Accepting…' : 'Accept invite'}
              </button>
            </form>
            {error && <div role="alert">{error}</div>}
          </div>
        )}

        {status === 'needauth' && (
          <div className="panel stack">
            <p>
              Please log in with the <b>invited email address</b> to accept
              this invitation.
            </p>
            <Link to="/login" className="btn btn-primary" style={{ width: 'fit-content' }}>
              Go to sign in
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="stack">
            <div role="alert">{error}</div>
            <Link to="/" className="link-grow">
              ← Back home
            </Link>
          </div>
        )}
      </main>
    </>
  )
}
