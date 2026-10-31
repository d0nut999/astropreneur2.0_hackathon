/**
 * API entry point: switches between real and mock based on VITE_USE_MOCK.
 */
import client from './client'
import { getMockResponse } from './mock'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

/**
 * Wrapper that uses mock or real API.
 */
async function api(method, path, data = null) {
  if (useMock) {
    const mock = await getMockResponse(method, path)
    if (mock) {
      return mock
    }
    console.warn(`No mock for ${method} ${path}`)
  }

  try {
    const config = { url: path, method }
    if (data) config.data = data

    const response = await client(config)
    return response
  } catch (error) {
    console.error(`API Error: ${method} ${path}`, error.response?.data || error.message)
    throw error
  }
}

// Convenience methods
export const apiGet = (path) => api('GET', path)
export const apiPost = (path, data) => api('POST', path, data)
export const apiPut = (path, data) => api('PUT', path, data)
export const apiDelete = (path) => api('DELETE', path)

export default client
