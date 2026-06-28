import api from './client';
import type { AnalyseResponse } from '../types/api';

const BASE_URL = 'http://localhost:8000';

export async function analyseText(sessionId: string, rawText: string): Promise<AnalyseResponse> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('raw_text', rawText);
  const { data } = await api.post<AnalyseResponse>('/analyse/text', formData);
  return data;
}

export async function analyseFile(sessionId: string, file: File, column: string): Promise<AnalyseResponse> {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('file', file);
  if (column && column.trim()) {
    formData.append('column', column.trim());
  }

  // Use native fetch — DO NOT set Content-Type; the browser sets multipart/form-data
  // with the correct boundary automatically. axios defaults can interfere with this.
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${BASE_URL}/analyse/file`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  const responseData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));

  if (!response.ok) {
    // Throw in a shape compatible with the UploadPage error handler
    const err = new Error(responseData.error || responseData.detail || `HTTP ${response.status}`) as Error & {
      response: { data: unknown; status: number };
    };
    err.response = { data: responseData, status: response.status };
    throw err;
  }

  return responseData as AnalyseResponse;
}
