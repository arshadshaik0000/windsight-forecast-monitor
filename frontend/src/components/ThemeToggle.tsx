'use client';

import React from 'react';
import { useTheme } from './ThemeProvider';

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      className="theme-toggle"
      onClick={toggle}
    >
      <span className="theme-toggle-thumb" data-active={isDark ? 'dark' : 'light'}>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="theme-icon"
        >
          {isDark ? (
            <path
              d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
              fill="currentColor"
            />
          ) : (
            <path
              d="M12 4a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V5a1 1 0 0 1 1-1Zm0 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7-2a1 1 0 0 1 1 1v0a1 1 0 0 1-1 1h-1a1 1 0 1 1 0-2h1ZM6 12a1 1 0 0 1-1 1H4a1 1 0 1 1 0-2h1a1 1 0 0 1 1 1Zm9.95 4.536a1 1 0 0 1 1.414 0l.707.707a1 1 0 0 1-1.414 1.414l-.707-.707a1 1 0 0 1 0-1.414Zm-8.486 0a1 1 0 0 1 0 1.414l-.707.707A1 1 0 1 1 4.343 17.243l.707-.707a1 1 0 0 1 1.414 0ZM12 18a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1Zm7.657-12.657a1 1 0 0 1 0 1.414l-.707.707a1 1 0 0 1-1.414-1.414l.707-.707a1 1 0 0 1 1.414 0Zm-13.314 0a1 1 0 0 1 1.414 0l.707.707A1 1 0 0 1 6.05 7.464l-.707-.707a1 1 0 0 1 0-1.414Z"
              fill="currentColor"
            />
          )}
        </svg>
      </span>
      <span className="theme-toggle-label">{isDark ? 'Dark' : 'Light'}</span>
    </button>
  );
}
