import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import HouseholdDetail from '../pages/HouseholdDetail'
import * as client from '../api/client'
import * as auth from '../auth/AuthContext'

const OWNER = { id: 1, display_name: 'Olive', email: 'o@x.com' }

function mockLoads(members) {
  vi.spyOn(client, 'api').mockImplementation(async (path) => {
    if (path === '/households/7') return { id: 7, name: 'Home', owner_id: 1 }
    if (path === '/households/7/members') return members
    if (path === '/households/7/lists') return []
    return null
  })
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/households/7']}>
      <Routes>
        <Route path="/households/:id" element={<HouseholdDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.spyOn(auth, 'useAuth').mockReturnValue({ user: OWNER, logout: () => {} })
})

test('owner sees a Remove button for members but not for the owner', async () => {
  mockLoads([
    { user_id: 1, display_name: 'Olive', email: 'o@x.com', role: 'owner' },
    { user_id: 2, display_name: 'Max', email: 'm@x.com', role: 'member' },
  ])
  renderDetail()

  await waitFor(() => expect(screen.getByText('Max')).toBeInTheDocument())
  const buttons = screen.getAllByRole('button', { name: /remove max/i })
  expect(buttons).toHaveLength(1)
  expect(screen.queryByRole('button', { name: /remove olive/i })).toBeNull()
})

test('clicking Remove deletes the member and refreshes the list', async () => {
  const apiSpy = vi.spyOn(client, 'api').mockImplementation(async (path, opts) => {
    if (path === '/households/7') return { id: 7, name: 'Home', owner_id: 1 }
    if (path === '/households/7/members') {
      // first load returns both; after delete, only the owner remains
      return apiSpy.mock.calls.some(([p, o]) => o?.method === 'DELETE')
        ? [{ user_id: 1, display_name: 'Olive', email: 'o@x.com', role: 'owner' }]
        : [
            { user_id: 1, display_name: 'Olive', email: 'o@x.com', role: 'owner' },
            { user_id: 2, display_name: 'Max', email: 'm@x.com', role: 'member' },
          ]
    }
    if (path === '/households/7/lists') return []
    return null
  })
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  renderDetail()

  await waitFor(() => expect(screen.getByText('Max')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /remove max/i }))

  await waitFor(() => expect(screen.queryByText('Max')).toBeNull())
  expect(apiSpy).toHaveBeenCalledWith('/households/7/members/2', { method: 'DELETE' })
})
