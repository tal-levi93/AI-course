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

  const [status, setStatus] = useState('working') // working | needauth | error
  const [error, setError] = useState('')

  useEffect(() => {
    if (!ready) return
    let active = true

    if (!getToken()) {
      setStatus('needauth')
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
