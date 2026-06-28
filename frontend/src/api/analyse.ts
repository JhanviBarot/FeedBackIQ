import axios from 'axios';
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
  // Use raw axios — do NOT set Content-Type manually; axios sets multipart/form-data
  // with the correct boundary automatically when given a FormData object.
  const { data } = await axios.post<AnalyseResponse>(
    `${BASE_URL}/analyse/file`,
    formData,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('access_token') ?? ''}`,
      },
    },
  );
  return data;
}
