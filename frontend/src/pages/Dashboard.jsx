import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext.jsx'
import TopBar from '../components/TopBar.jsx'

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [households, setHouseholds] = useState([])
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [code, setCode] = useState('')
  const [joinError, setJoinError] = useState('')
  const [joinBusy, setJoinBusy] = useState(false)

  async function load() {
    try {
      setHouseholds(await api('/households'))
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch data on mount
    load()
  }, [])

  async function createHousehold(e) {
    e.preventDefault()
    if (!name.trim()) return
    setError('')
    setBusy(true)
    try {
      await api('/households', { method: 'POST', body: { name: name.trim() } })
      setName('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function joinHousehold(e) {
    e.preventDefault()
    if (!code.trim()) return
    setJoinError('')
    setJoinBusy(true)
    try {
      const res = await api('/invitations/accept', {
        method: 'POST',
        body: { token: code.trim() },
      })
      setCode('')
      navigate(`/households/${res.household_id}`)
    } catch (err) {
      setJoinError(err.message || 'Could not join household')
    } finally {
      setJoinBusy(false)
    }
  }

  return (
    <>
      <TopBar />
      <main className="shell stack reveal">
        <div>
          <p className="eyebrow">Your kitchens</p>
          <h1>
            Good to see you, <em>{user?.display_name}.</em>
          </h1>
        </div>

        <section className="panel stack">
          <div className="between">
            <h2>Households</h2>
            <span className="badge">{households.length}</span>
          </div>
          <hr className="divider" />
          {households.length === 0 ? (
            <p className="muted">
              No households yet. Start one below and invite the people you
              share a kitchen with.
            </p>
          ) : (
            <div className="stack">
              {households.map((h) => (
                <Link key={h.id} to={`/households/${h.id}`} className="tile">
                  <span className="name">{h.name}</span>
                  <span className="muted mono">#{h.id}</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="panel panel-2 stack">
          <h3>Start a new household</h3>
          <form className="row wrap" onSubmit={createHousehold}>
            <input
              className="grow"
              type="text"
              aria-label="household name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="The Levi kitchen"
            />
            <button className="btn-primary" type="submit" disabled={busy}>
              {busy ? 'Creating…' : 'Create'}
            </button>
          </form>
          {error && <div role="alert">{error}</div>}
        </section>

        <section className="panel panel-2 stack">
          <h3>Connect to an online household</h3>
          <p className="muted">
            Got an invite code? Paste it to join a household someone shared
            with you. You must be signed in with the <b>invited email
            address</b>.
          </p>
          <form className="row wrap" onSubmit={joinHousehold}>
            <input
              className="grow mono"
              type="text"
              aria-label="invite code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste invite code"
            />
            <button className="btn-primary" type="submit" disabled={joinBusy}>
              {joinBusy ? 'Joining…' : 'Join household'}
            </button>
          </form>
          {joinError && <div role="alert">{joinError}</div>}
        </section>
      </main>
    </>
  )
}
