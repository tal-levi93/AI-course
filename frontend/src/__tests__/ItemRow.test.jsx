import { render, screen, fireEvent } from '@testing-library/react'
import ItemRow from '../components/ItemRow'

test('toggling checkbox calls onToggle with new state', () => {
  const onToggle = vi.fn()
  render(<ItemRow item={{ id: 1, name: 'Milk', is_checked: false }} onToggle={onToggle} onDelete={() => {}} />)
  fireEvent.click(screen.getByRole('checkbox'))
  expect(onToggle).toHaveBeenCalledWith(1, true)
})
