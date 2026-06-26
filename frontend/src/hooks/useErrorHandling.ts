import { useState, useCallback } from 'react';
import { AxiosError } from 'axios';

interface FieldError {
  field: string;
  message: string;
}

interface ErrorState {
  message: string | null;
  fieldErrors: FieldError[];
  type: 'general' | 'field' | 'not_found' | 'access_denied' | 'not_ready' | 'server';
}

export function useErrorHandling() {
  const [error, setError] = useState<ErrorState>({ message: null, fieldErrors: [], type: 'general' });

  const handleError = useCallback((err: unknown): ErrorState => {
    if (!(err instanceof AxiosError)) {
      const state: ErrorState = { message: 'An unexpected error occurred', fieldErrors: [], type: 'general' };
      setError(state);
      return state;
    }

    const status = err.response?.status;
    const data = err.response?.data;

    if (status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      const state: ErrorState = { message: 'Session expired. Please log in again.', fieldErrors: [], type: 'general' };
      setError(state);
      return state;
    }

    if (status === 403) {
      const state: ErrorState = { message: 'Access denied.', fieldErrors: [], type: 'access_denied' };
      setError(state);
      return state;
    }

    if (status === 404) {
      const state: ErrorState = { message: 'Not found.', fieldErrors: [], type: 'not_found' };
      setError(state);
      return state;
    }

    if (status === 422 && data?.detail) {
      const fieldErrors: FieldError[] = [];
      if (Array.isArray(data.detail)) {
        for (const item of data.detail) {
          if (item.loc && item.msg) {
            const field = item.loc[item.loc.length - 1];
            fieldErrors.push({ field: String(field), message: item.msg });
          }
        }
      }
      const state: ErrorState = { message: null, fieldErrors, type: 'field' };
      setError(state);
      return state;
    }

    if (status === 425) {
      const state: ErrorState = { message: 'Analysis not ready. Please wait for classification to complete.', fieldErrors: [], type: 'not_ready' };
      setError(state);
      return state;
    }

    if (status === 500) {
      const state: ErrorState = { message: 'Server error. Please try again later.', fieldErrors: [], type: 'server' };
      setError(state);
      return state;
    }

    const message = data?.detail || data?.message || err.message || 'An error occurred';
    const state: ErrorState = { message, fieldErrors: [], type: 'general' };
    setError(state);
    return state;
  }, []);

  const clearError = useCallback(() => {
    setError({ message: null, fieldErrors: [], type: 'general' });
  }, []);

  const getFieldError = useCallback((field: string): string | null => {
    return error.fieldErrors.find(e => e.field === field)?.message || null;
  }, [error.fieldErrors]);

  return { error, handleError, clearError, getFieldError };
}
