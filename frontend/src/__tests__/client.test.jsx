import { getToken } from '../api/client'
test('getToken returns null when unset', () => {
  localStorage.removeItem('token')
  expect(getToken()).toBeNull()
})
