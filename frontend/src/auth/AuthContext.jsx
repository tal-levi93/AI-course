import { createContext, useContext, useState, useCallback } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  const refresh = useCallback(async () => {
    if (!localStorage.getItem('token')) {
      setReady(true)
      return
    }
    try {
      const me = await api('/auth/me')
      setUser(me)
    } catch {
      localStorage.removeItem('token')
      setUser(null)
    } finally {
      setReady(true)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await api('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    })
    localStorage.setItem('token', data.access_token)
    const me = await api('/auth/me')
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{ user, ready, refresh, login, logout, setUser }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components -- colocated context hook; not worth splitting files for an HMR-only rule
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
