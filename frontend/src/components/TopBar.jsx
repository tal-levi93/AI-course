import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

export function Wordmark() {
  return (
    <Link to="/" className="wordmark" aria-label="Shoply home">
      <svg
        className="mark"
        viewBox="0 0 48 48"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M16 18 C10 16 10 9 16 8 C22 7 27 9 26 4" />
        <path d="M16 18 L19 30 H35 L40 18 Z" />
        <circle cx="24" cy="36" r="2.8" fill="currentColor" stroke="none" />
        <circle cx="33" cy="36" r="2.8" fill="currentColor" stroke="none" />
      </svg>
      shoply
    </Link>
  )
}

export default function TopBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Wordmark />
        {user && (
          <div className="row">
            <span className="who">
              Signed in as <b>{user.display_name}</b>
            </span>
            <button className="btn-ghost" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
