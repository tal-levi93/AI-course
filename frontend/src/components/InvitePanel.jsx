import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '../api/client'

export default function InvitePanel({ householdId }) {
  const [email, setEmail] = useState('')
  const [invite, setInvite] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState('')

  async function send(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = await api(`/households/${householdId}/invitations`, {
        method: 'POST',
        body: { email },
      })
      setInvite(result)
      setEmail('')
    } catch (err) {
      setError(err.message || 'Could not send invite')
    } finally {
      setBusy(false)
    }
  }

  async function copy(text, which) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(which)
      setTimeout(() => setCopied(''), 1500)
    } catch {
      setError('Could not copy to clipboard')
    }
  }

  return (
    <section className="panel stack">
      <div>
        <p className="eyebrow">Invite a housemate</p>
        <h3>Send an invitation</h3>
      </div>
      <form className="row wrap" onSubmit={send}>
        <input
          className="grow"
          type="email"
          aria-label="invite email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="housemate@home.com"
        />
        <button className="btn-accent" type="submit" disabled={busy}>
          {busy ? 'Sending…' : 'Send invite'}
        </button>
      </form>

      {error && <div role="alert">{error}</div>}

      {invite && (
        <div className="stack">
          <hr className="divider" />
          <p className="muted">
            Invitation created for <b>{invite.email}</b>. Share this token — it
            is shown only once.
          </p>
          <div className="receipt stack">
            <div>
              <span className="lbl">Invite token</span>
              <div className="token">{invite.token}</div>
            </div>
            <div className="row wrap">
              <button
                className="btn-ghost"
                type="button"
                onClick={() => copy(invite.token, 'token')}
              >
                {copied === 'token' ? 'Copied!' : 'Copy token'}
              </button>
              <button
                className="btn-ghost"
                type="button"
                onClick={() => copy(invite.accept_url, 'link')}
              >
                {copied === 'link' ? 'Copied!' : 'Copy link'}
              </button>
            </div>
          </div>
          <div className="row wrap">
            <div className="qr-card">
              <QRCodeSVG
                value={invite.accept_url}
                size={132}
                fgColor="#21281F"
                bgColor="#ffffff"
                level="M"
              />
            </div>
            <p className="muted" style={{ maxWidth: 220 }}>
              Scan to accept. The invitee must sign in with{' '}
              <b>{invite.email}</b>.
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
