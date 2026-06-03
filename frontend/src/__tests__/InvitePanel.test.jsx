import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import InvitePanel from '../components/InvitePanel'
import * as client from '../api/client'

test('shows token and QR after creating invite', async () => {
  vi.spyOn(client, 'api').mockResolvedValue({
    id: 1, email: 'g@b.com', token: 'TOK123', accept_url: 'http://x/accept?token=TOK123',
    expires_at: '2026-06-10T00:00:00Z',
  })
  render(<InvitePanel householdId={1} />)
  fireEvent.change(screen.getByLabelText('invite email'), { target: { value: 'g@b.com' } })
  fireEvent.click(screen.getByText('Send invite'))
  await waitFor(() => expect(screen.getByText(/TOK123/)).toBeInTheDocument())
})
