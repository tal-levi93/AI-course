import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

export function Wordmark() {
  return (
    <Link to="/" className="wordmark" aria-label="Pantry home">
      <span className="mark" aria-hidden="true" />
      Pantry
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
