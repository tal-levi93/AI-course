import { useEffect, useRef } from 'react'
import { getToken } from '../api/client'

const WS_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(
  /^http/,
  'ws',
)

export function useHouseholdSocket(householdId, onEvent) {
  const cbRef = useRef(onEvent)
  useEffect(() => {
    cbRef.current = onEvent
  })

  useEffect(() => {
    if (!Number.isInteger(householdId) || householdId <= 0) return

    const url = `${WS_BASE}/ws/households/${householdId}?token=${getToken()}`
    const socket = new WebSocket(url)

    socket.onmessage = (e) => {
      try {
        cbRef.current(JSON.parse(e.data))
      } catch {
        /* ignore malformed payloads */
      }
    }

    return () => {
      socket.close()
    }
  }, [householdId])
}

export default useHouseholdSocket
