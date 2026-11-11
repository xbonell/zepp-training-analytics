import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(cleanup)

Object.defineProperty(window, 'matchMedia', {
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
})

// Pin the default locale so date assertions don't depend on the shell's LANG.
const NativeDateTimeFormat = Intl.DateTimeFormat
Intl.DateTimeFormat = function (
  locales?: Intl.LocalesArgument,
  options?: Intl.DateTimeFormatOptions,
) {
  return new NativeDateTimeFormat(locales ?? 'en-US', options)
} as typeof Intl.DateTimeFormat
