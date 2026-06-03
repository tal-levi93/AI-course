import { groupByCategory } from '../lib/groupByCategory'

const item = (id, category) => ({ id, name: `n${id}`, category })

test('returns groups in the fixed category order, omitting empty ones', () => {
  const result = groupByCategory([
    item(1, 'Bakery'),
    item(2, 'Fruit & Vegetables'),
    item(3, 'Drinks'),
  ])
  expect(result.map((g) => g.category)).toEqual([
    'Fruit & Vegetables',
    'Bakery',
    'Drinks',
  ])
})

test('preserves original order within a group', () => {
  const result = groupByCategory([
    item(1, 'Bakery'),
    item(2, 'Bakery'),
    item(3, 'Bakery'),
  ])
  expect(result).toHaveLength(1)
  expect(result[0].items.map((i) => i.id)).toEqual([1, 2, 3])
})

test('buckets null and unrecognized categories under Other', () => {
  const result = groupByCategory([
    item(1, null),
    item(2, 'Nonsense'),
    item(3, undefined),
  ])
  expect(result).toHaveLength(1)
  expect(result[0].category).toBe('Other')
  expect(result[0].items.map((i) => i.id)).toEqual([1, 2, 3])
})

test('returns an empty array for no items', () => {
  expect(groupByCategory([])).toEqual([])
})
