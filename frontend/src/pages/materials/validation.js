export const IMAGE_MAX_BYTES = 5 * 1024 * 1024
export const VIDEO_MAX_BYTES = 30 * 1024 * 1024

export const characterCount = value => Array.from(value).length
// Match Python str.strip(), including U+0085/control whitespace (not U+FEFF).
export const normalizeTitle = value => value.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/gu, '')

export function titleError(value) {
  const count = characterCount(normalizeTitle(value))
  return count < 1 || count > 100 ? '자료 제목은 앞뒤 공백을 제외하고 1~100자로 입력해 주세요.' : ''
}

export function memoError(value) {
  return characterCount(value) > 1000 ? '메모는 1,000자 이하로 입력해 주세요.' : ''
}

const fileTypes = {
  png: { label: 'PNG 이미지', mime: 'image/png', max: IMAGE_MAX_BYTES },
  jpg: { label: 'JPG 이미지', mime: 'image/jpeg', max: IMAGE_MAX_BYTES },
  jpeg: { label: 'JPG 이미지', mime: 'image/jpeg', max: IMAGE_MAX_BYTES },
  mp4: { label: 'MP4 영상', mime: 'video/mp4', max: VIDEO_MAX_BYTES },
}

export function inspectSelection(files) {
  if (files.length !== 1) return { error: '자료당 파일을 한 개만 선택해 주세요.' }
  const file = files[0]
  const extension = file.name.split('.').pop().toLowerCase()
  const type = file.name.includes('.') && Object.hasOwn(fileTypes, extension) ? fileTypes[extension] : undefined
  if (!type || (file.type && file.type !== type.mime)) {
    return { error: 'PNG·JPG(JPEG) 이미지 또는 MP4 영상만 선택할 수 있어요.' }
  }
  if (file.size === 0) return { error: '내용이 없는 파일은 선택할 수 없어요.' }
  if (file.size > type.max) {
    return { error: type.max === IMAGE_MAX_BYTES ? '이미지는 최대 5MiB까지 선택할 수 있어요.' : '영상은 최대 30MiB까지 선택할 수 있어요.' }
  }
  // This only checks browser metadata. The upload API must inspect real bytes in M3.
  return { file, label: type.label, error: '' }
}

export function formatFileSize(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(2)}MiB (${bytes.toLocaleString('ko-KR')}바이트)`
}
