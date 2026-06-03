import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import './App.css'
import { useAuth } from './auth/AuthContext.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import AcceptInvite from './pages/AcceptInvite.jsx'
import Dashboard from './pages/Dashboard.jsx'
import HouseholdDetail from './pages/HouseholdDetail.jsx'
import ListView from './pages/ListView.jsx'

function Protected({ children }) {
  const { user, ready } = useAuth()
  if (!ready)
    return (
      <div className="center-screen">
        <p className="muted mono">Loading your pantry…</p>
      </div>
    )
  if (!user) return <Navigate to="/login" replace />
  return children
}

function App() {
  const { refresh } = useAuth()

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/accept" element={<AcceptInvite />} />
      <Route
        path="/"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/households/:id"
        element={
          <Protected>
            <HouseholdDetail />
          </Protected>
        }
      />
      <Route
        path="/lists/:listId"
        element={
          <Protected>
            <ListView />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
