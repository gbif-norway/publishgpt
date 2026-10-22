// The API ingress refuses request bodies a little over the upload limit (it allows for multipart
// overhead) before they reach ChatIPT. Its 413 reply has no CORS headers, so the browser reports
// only a failed request: check sizes first.
const MB = 1024 * 1024

export const parseUploadLimitMB = (value, fallback) => {
  const limit = Number(value)
  return Number.isFinite(limit) && limit > 0 ? limit : fallback
}

// Rounds up, so a size just over the limit never reads as equal to it.
export const formatFileSize = bytes => bytes < MB
  ? `${Math.max(1, Math.ceil(bytes / 1024))} KB`
  : `${(Math.ceil(bytes / MB * 10) / 10).toFixed(1)} MB`

export const exceedsUploadLimit = (file, limitMB) => file.size > limitMB * MB

// For files sent one per request.
export function oversizedFilesError(files, limitMB) {
  const large = files.filter(file => exceedsUploadLimit(file, limitMB))
  if (!large.length) return null
  const names = large.map(file => `${file.name} (${formatFileSize(file.size)})`).join(', ')
  return `${names} ${large.length === 1 ? 'is' : 'are'} larger than the ${limitMB} MB upload limit.`
}

// For files sent together in one request.
export function uploadSizeError(files, limitMB) {
  if (files.length < 2) return oversizedFilesError(files, limitMB)
  const total = files.reduce((sum, file) => sum + file.size, 0)
  if (total <= limitMB * MB) return null
  return `These files total ${formatFileSize(total)}, more than the ${limitMB} MB upload limit. Remove some files to continue.`
}

// An upload the ingress refuses makes fetch reject rather than resolve with the 413.
export async function sendUpload(url, options, limitMB, fetchImpl = fetch) {
  let response
  try {
    response = await fetchImpl(url, options)
  } catch {
    throw new Error(`We couldn't confirm the upload. Check your connection and try again. Uploads can be at most ${limitMB} MB.`)
  }
  if (response.status === 413) throw new Error(`The upload is larger than the ${limitMB} MB limit.`)
  return response
}
