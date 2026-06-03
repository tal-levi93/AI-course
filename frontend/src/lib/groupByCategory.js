import { CATEGORIES, DEFAULT_CATEGORY } from '../constants/categories'

// Group items into the fixed CATEGORIES order. Items whose category is missing
// or unrecognized fall under DEFAULT_CATEGORY. Empty groups are omitted and
// within-group order is preserved.
export function groupByCategory(items) {
  const buckets = new Map(CATEGORIES.map((c) => [c, []]))
  for (const item of items) {
    const key = buckets.has(item.category) ? item.category : DEFAULT_CATEGORY
    buckets.get(key).push(item)
  }
  return CATEGORIES.filter((c) => buckets.get(c).length > 0).map((c) => ({
    category: c,
    items: buckets.get(c),
  }))
}
