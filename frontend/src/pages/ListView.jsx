import { useEffect, useState, useCallback } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import TopBar from '../components/TopBar.jsx'
import ItemRow from '../components/ItemRow.jsx'
import { useHouseholdSocket } from '../hooks/useHouseholdSocket.js'

export default function ListView() {
  const { listId } = useParams()
  const [searchParams] = useSearchParams()
  const household = searchParams.get('household')
  const listIdNum = Number(listId)

  const [items, setItems] = useState([])
  const [name, setName] = useState('')
  const [quantity, setQuantity] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setItems(await api(`/lists/${listId}/items`))
    } catch (err) {
      setError(err.message)
    }
  }, [listId])

  useEffect(() => {
    load()
  }, [load])

  useHouseholdSocket(Number(household), (msg) => {
    if (!msg || !msg.type) return
    if (msg.type === 'item.added' || msg.type === 'item.updated') {
      if (msg.item && msg.item.list_id === listIdNum) {
        setItems((prev) => {
          const idx = prev.findIndex((i) => i.id === msg.item.id)
          if (idx === -1) return [...prev, msg.item]
          const next = prev.slice()
          next[idx] = msg.item
          return next
        })
      }
    } else if (msg.type === 'item.deleted') {
      if (msg.list_id === listIdNum) {
        setItems((prev) => prev.filter((i) => i.id !== msg.item_id))
      }
    }
  })

  async function addItem(e) {
    e.preventDefault()
    if (!name.trim()) return
    setError('')
    setBusy(true)
    try {
      await api(`/lists/${listId}/items`, {
        method: 'POST',
        body: { name: name.trim(), quantity: quantity.trim() || undefined },
      })
      setName('')
      setQuantity('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function toggle(itemId, checked) {
    try {
      await api(`/items/${itemId}`, {
        method: 'PATCH',
        body: { is_checked: checked },
      })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function remove(itemId) {
    try {
      await api(`/items/${itemId}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const remaining = items.filter((i) => !i.is_checked).length

  return (
    <>
      <TopBar />
      <main className="shell stack reveal">
        <div>
          {household ? (
            <Link to={`/households/${household}`} className="link-grow">
              ← Back to household
            </Link>
          ) : (
            <Link to="/" className="link-grow">
              ← Home
            </Link>
          )}
          <p className="eyebrow" style={{ marginTop: 14 }}>
            Shopping list
          </p>
          <h1>
            {remaining} <em>to gather</em>
          </h1>
        </div>

        {error && <div role="alert">{error}</div>}

        <section className="panel panel-2 stack">
          <h3>Add an item</h3>
          <form className="row wrap" onSubmit={addItem}>
            <input
              className="grow"
              type="text"
              aria-label="item name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Sourdough, olive oil, lemons…"
            />
            <input
              className="qty-input"
              type="text"
              aria-label="quantity"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="2 · 500g · 1 dozen"
            />
            <button className="btn-accent" type="submit" disabled={busy}>
              {busy ? 'Adding…' : 'Add'}
            </button>
          </form>
        </section>

        <section className="panel">
          {items.length === 0 ? (
            <p className="muted">The list is empty. Add the first thing.</p>
          ) : (
            <div>
              {items.map((item) => (
                <ItemRow
                  key={item.id}
                  item={item}
                  onToggle={toggle}
                  onDelete={remove}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </>
  )
}
