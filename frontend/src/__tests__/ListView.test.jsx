import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ListView from '../pages/ListView'
import * as client from '../api/client'
import * as auth from '../auth/AuthContext'

// useHouseholdSocket opens a real WebSocket; stub it out for the test.
vi.mock('../hooks/useHouseholdSocket.js', () => ({
  useHouseholdSocket: () => {},
}))

function renderList() {
  return render(
    <MemoryRouter initialEntries={['/lists/5?household=7']}>
      <Routes>
        <Route path="/lists/:listId" element={<ListView />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.spyOn(auth, 'useAuth').mockReturnValue({
    user: { id: 1, display_name: 'Olive' },
    logout: () => {},
  })
})

test('adding an item sends the typed quantity', async () => {
  const apiSpy = vi.spyOn(client, 'api').mockResolvedValue([])
  renderList()
  await waitFor(() => expect(apiSpy).toHaveBeenCalledWith('/lists/5/items'))

  fireEvent.change(screen.getByLabelText('item name'), { target: { value: 'Milk' } })
  fireEvent.change(screen.getByLabelText('quantity'), { target: { value: '2 cartons' } })
  fireEvent.click(screen.getByRole('button', { name: /^add$/i }))

  await waitFor(() =>
    expect(apiSpy).toHaveBeenCalledWith('/lists/5/items', {
      method: 'POST',
      body: { name: 'Milk', quantity: '2 cartons' },
    })
  )
})

test('adding an item with no quantity omits the quantity key', async () => {
  const apiSpy = vi.spyOn(client, 'api').mockResolvedValue([])
  renderList()
  await waitFor(() => expect(apiSpy).toHaveBeenCalledWith('/lists/5/items'))

  fireEvent.change(screen.getByLabelText('item name'), { target: { value: 'Eggs' } })
  fireEvent.click(screen.getByRole('button', { name: /^add$/i }))

  await waitFor(() =>
    expect(apiSpy).toHaveBeenCalledWith('/lists/5/items', {
      method: 'POST',
      body: { name: 'Eggs', quantity: undefined },
    })
  )
})
