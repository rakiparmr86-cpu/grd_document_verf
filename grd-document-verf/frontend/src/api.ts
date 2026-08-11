export type Session = {
  access_token: string
  display_name: string
  email: string
  role: string
  permissions: string[]
}

export type CaseDocument = {
  id: string
  filename: string
  document_type: string
  detected_file_type: string
  size_bytes: number
  page_count: number
  password_protected: boolean
  status: string
  malware_scan_status: string
  storage_available: boolean
  storage_deleted_at: string | null
  observations: string[]
  updated_at: string
}

export type CaseItem = {
  id: string
  name: string
  reference: string | null
  status: string
  documents: CaseDocument[]
  updated_at: string
}

export type LoginRequest = {
  email: string
  password: string
  requested_role: string
  business_type: string
}

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

export const API_BASE_URL = (configuredBaseUrl || '/api').replace(/\/$/, '')

type ApiRequestOptions = Omit<RequestInit, 'body' | 'method'>

export class ApiError extends Error {
  readonly status: number
  readonly retryAfter: string | null

  constructor(message: string, status = 0, retryAfter: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfter = retryAfter
  }
}

function buildUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

function isNativeRequestBody(body: unknown): body is BodyInit {
  return (
    typeof body === 'string' ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof Blob ||
    body instanceof ArrayBuffer
  )
}

async function parseResponse(response: Response): Promise<unknown> {
  const text = await response.text()

  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function errorMessage(payload: unknown, fallback: string) {
  if (typeof payload === 'string' && payload) {
    return payload
  }

  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = payload.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = detail.message
      return typeof message === 'string' ? message : fallback
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === 'object' && 'msg' in item ? item.msg : null,
        )
        .filter((message): message is string => typeof message === 'string')

      if (messages.length) {
        return messages.join(', ')
      }
    }
  }

  return fallback
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: ApiRequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')

  let requestBody: BodyInit | undefined

  if (body !== undefined) {
    if (isNativeRequestBody(body)) {
      requestBody = body
    } else {
      headers.set('Content-Type', 'application/json')
      requestBody = JSON.stringify(body)
    }
  }

  let response: Response

  try {
    response = await fetch(buildUrl(path), {
      ...options,
      method,
      headers,
      body: requestBody,
    })
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_BASE_URL}.`)
  }

  const payload = await parseResponse(response)

  if (!response.ok) {
    throw new ApiError(
      errorMessage(payload, `Request failed (${response.status}).`),
      response.status,
      response.headers.get('Retry-After'),
    )
  }

  return payload as T
}

export const apiClient = {
  get<T>(path: string, options?: ApiRequestOptions) {
    return request<T>('GET', path, undefined, options)
  },

  post<T>(path: string, body?: unknown, options?: ApiRequestOptions) {
    return request<T>('POST', path, body, options)
  },

  put<T>(path: string, body?: unknown, options?: ApiRequestOptions) {
    return request<T>('PUT', path, body, options)
  },

  patch<T>(path: string, body?: unknown, options?: ApiRequestOptions) {
    return request<T>('PATCH', path, body, options)
  },

  delete<T>(path: string, options?: ApiRequestOptions) {
    return request<T>('DELETE', path, undefined, options)
  },
}

function authenticatedOptions(accessToken: string): ApiRequestOptions {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  }
}

export const grdApi = {
  login(payload: LoginRequest) {
    return apiClient.post<Session>('/v1/auth/login', payload)
  },

  getCases(accessToken: string) {
    return apiClient.get<CaseItem[]>('/v1/cases', authenticatedOptions(accessToken))
  },

  createCase(accessToken: string, name: string) {
    return apiClient.post<CaseItem>(
      '/v1/cases',
      { name },
      authenticatedOptions(accessToken),
    )
  },

  uploadDocument(accessToken: string, file: File, documentType: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', documentType)

    return apiClient.post<unknown>(
      '/v1/documents',
      formData,
      authenticatedOptions(accessToken),
    )
  },

  retryDocument(accessToken: string, documentId: string) {
    return apiClient.post<unknown>(
      `/v1/documents/${documentId}/retry`,
      undefined,
      authenticatedOptions(accessToken),
    )
  },
}

export function getApiError(error: unknown, fallback: string) {
  return error instanceof ApiError ? error : new ApiError(fallback)
}
