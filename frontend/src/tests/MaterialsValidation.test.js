import { expect, test } from 'vitest'
import { IMAGE_MAX_BYTES, VIDEO_MAX_BYTES, titleError, memoError, normalizeTitle, inspectSelection } from '../pages/materials/validation.js'

test.each(['', ' ', '\n\t', '가'.repeat(101)])('rejects invalid title length: %j', value => {
  expect(titleError(value)).not.toBe('')
})
test.each(['가', '가'.repeat(100), '😀'.repeat(100), '  한  글 \n'])('accepts normalized title: %j', value => {
  expect(titleError(value)).toBe('')
})
test('preserves internal spaces and optional memo boundaries', () => {
  expect(normalizeTitle('  오늘  공부  ')).toBe('오늘  공부')
  expect(memoError('')).toBe('')
  expect(memoError('가'.repeat(1000))).toBe('')
  expect(memoError('😀'.repeat(1000))).toBe('')
  expect(memoError('가'.repeat(1001))).not.toBe('')
})
test.each([
  ['capture.PNG', 'image/png', IMAGE_MAX_BYTES],
  ['capture.jpg', 'image/jpeg', IMAGE_MAX_BYTES],
  ['capture.JPEG', '', IMAGE_MAX_BYTES],
  ['lesson.MP4', 'video/mp4', VIDEO_MAX_BYTES],
])('accepts exact byte limit for %s and rejects one byte over', (name, type, size) => {
  // Metadata objects avoid allocating 30MiB buffers for client-only boundary checks.
  expect(inspectSelection([{ name, type, size }]).error).toBe('')
  expect(inspectSelection([{ name, type, size: size + 1 }]).error).not.toBe('')
})
const invalidSelections = [
  [], [{ name: 'empty.png', type: 'image/png', size: 0 }],
  [{ name: 'notes.txt', type: 'text/plain', size: 10 }],
  [{ name: 'fake.png', type: 'text/plain', size: 10 }],
  [{ name: 'capture', type: 'image/png', size: 10 }],
  [{ name: 'file.constructor', type: '', size: 10 }],
  [{ name: 'a.png', type: 'image/png', size: 10 }, { name: 'b.jpg', type: 'image/jpeg', size: 10 }],
]
test.each(invalidSelections.map(files => ({ files })))('rejects unsupported or invalid selection %#', ({ files }) => {
  expect(inspectSelection(files).error).not.toBe('')
})
