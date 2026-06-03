import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext.jsx'
import TopBar from '../components/TopBar.jsx'
import InvitePanel from '../components/InvitePanel.jsx'

export default function HouseholdDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const [household, setHousehold] = useState(null)
  const [members, setMembers] = useState([])
  const [lists, setLists] = useState([])
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [removingId, setRemovingId] = useState(null)

  const isOwner = household?.owner_id === user?.id

  async function loadMembers() {
    setMembers(await api(`/households/${id}/members`))
  }

  async function loadLists() {
    setLists(await api(`/households/${id}/lists`))
  }

  async function removeMember(member) {
    if (!window.confirm(`Remove ${member.display_name}?`)) return
    setError('')
    setRemovingId(member.user_id)
    try {
      await api(`/households/${id}/members/${member.user_id}`, {
        method: 'DELETE',
      })
      await loadMembers()
    } catch (err) {
      setError(err.message)
    } finally {
      setRemovingId(null)
    }
  }

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const [h, m, l] = await Promise.all([
          api(`/households/${id}`),
          api(`/households/${id}/members`),
          api(`/households/${id}/lists`),
        ])
        if (!active) return
        setHousehold(h)
        setMembers(m)
        setLists(l)
      } catch (err) {
        if (active) setError(err.message)
      }
    })()
    return () => {
      active = false
    }
  }, [id])

  async function createList(e) {
    e.preventDefault()
    if (!name.trim()) return
    setError('')
    setBusy(true)
    try {
      await api(`/households/${id}/lists`, {
        method: 'POST',
        body: { name: name.trim() },
      })
      setName('')
      await loadLists()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <TopBar />
      <main className="shell stack reveal">
        <div>
          <Link to="/" className="link-grow">
            ← All households
          </Link>
          <p className="eyebrow" style={{ marginTop: 14 }}>
            Household
          </p>
          <h1>{household ? household.name : '…'}</h1>
        </div>

        {error && <div role="alert">{error}</div>}

        <section className="panel stack">
          <h2>Members</h2>
          <hr className="divider" />
          <div className="stack">
            {members.map((m) => (
              <div key={m.user_id} className="between">
                <span>{m.display_name}</span>
                <div className="row">
                  <span
                    className={`badge${m.role === 'owner' ? ' badge-owner' : ''}`}
                  >
                    {m.role}
                  </span>
                  {isOwner && m.role !== 'owner' && (
                    <button
                      className="btn-ghost"
                      type="button"
                      aria-label={`Remove ${m.display_name}`}
                      disabled={removingId === m.user_id}
                      onClick={() => removeMember(m)}
                    >
                      {removingId === m.user_id ? 'Removing…' : 'Remove'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <InvitePanel householdId={Number(id)} />

        <section className="panel stack">
          <div className="between">
            <h2>Shopping lists</h2>
            <span className="badge">{lists.length}</span>
          </div>
          <hr className="divider" />
          {lists.length === 0 ? (
            <p className="muted">No lists yet. Create your first one below.</p>
          ) : (
            <div className="stack">
              {lists.map((l) => (
                <Link
                  key={l.id}
                  to={`/lists/${l.id}?household=${id}`}
                  className="tile"
                >
                  <span className="name">{l.name}</span>
                  <span className="muted mono">open →</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="panel panel-2 stack">
          <h3>New list</h3>
          <form className="row wrap" onSubmit={createList}>
            <input
              className="grow"
              type="text"
              aria-label="list name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Weekly groceries"
            />
            <button className="btn-primary" type="submit" disabled={busy}>
              {busy ? 'Creating…' : 'Create'}
            </button>
          </form>
        </section>
      </main>
    </>
  )
}
