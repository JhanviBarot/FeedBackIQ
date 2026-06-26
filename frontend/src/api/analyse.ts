import api from './client';
import type { AnalyseResponse } from '../types/api';

export async function analyseText(sessionId: string, rawText: string): Promise<AnalyseResponse> {
  const params = new URLSearchParams();
  params.append('session_id', sessionId);
  params.append('raw_text', rawText);
  const { data } = await api.post<AnalyseResponse>('/analyse/text', params);
  return data;
}

export async function analyseFile(sessionId: string, file: File, column: string): Promise<AnalyseResponse> {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('file', file);
  form.append('column', column);
  const { data } = await api.post<AnalyseResponse>('/analyse/file', form);
  return data;
}
