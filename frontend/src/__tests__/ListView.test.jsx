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

test('adding an item sends the typed quantity and selected category', async () => {
  const apiSpy = vi.spyOn(client, 'api').mockResolvedValue([])
  renderList()
  await waitFor(() => expect(apiSpy).toHaveBeenCalledWith('/lists/5/items'))

  fireEvent.change(screen.getByLabelText('item name'), { target: { value: 'Milk' } })
  fireEvent.change(screen.getByLabelText('quantity'), { target: { value: '2 cartons' } })
  fireEvent.change(screen.getByLabelText('category'), { target: { value: 'Dairy & Eggs' } })
  fireEvent.click(screen.getByRole('button', { name: /^add$/i }))

  await waitFor(() =>
    expect(apiSpy).toHaveBeenCalledWith('/lists/5/items', {
      method: 'POST',
      body: { name: 'Milk', quantity: '2 cartons', category: 'Dairy & Eggs' },
    })
  )
})

test('adding an item defaults the category to Other and omits empty quantity', async () => {
  const apiSpy = vi.spyOn(client, 'api').mockResolvedValue([])
  renderList()
  await waitFor(() => expect(apiSpy).toHaveBeenCalledWith('/lists/5/items'))

  fireEvent.change(screen.getByLabelText('item name'), { target: { value: 'Eggs' } })
  fireEvent.click(screen.getByRole('button', { name: /^add$/i }))

  await waitFor(() =>
    expect(apiSpy).toHaveBeenCalledWith('/lists/5/items', {
      method: 'POST',
      body: { name: 'Eggs', quantity: undefined, category: 'Other' },
    })
  )
})

test('renders items grouped under category headings in fixed order', async () => {
  vi.spyOn(client, 'api').mockResolvedValue([
    { id: 1, name: 'Steak', category: 'Meat & Fish', is_checked: false },
    { id: 2, name: 'Apples', category: 'Fruit & Vegetables', is_checked: false },
  ])
  renderList()

  // Wait for the loaded items to render before reading the headings.
  await screen.findByText('Apples')
  const groupHeadings = screen
    .getAllByRole('heading', { level: 3 })
    .map((h) => h.textContent)
    .filter((t) => t === 'Fruit & Vegetables' || t === 'Meat & Fish')
  expect(groupHeadings).toEqual(['Fruit & Vegetables', 'Meat & Fish'])
})
