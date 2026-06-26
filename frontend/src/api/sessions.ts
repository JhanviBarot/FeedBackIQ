import api from './client';
import type { CreateSessionResponse, SessionsListResponse, ProfileData } from '../types/api';

export async function createSession(profile: ProfileData): Promise<CreateSessionResponse> {
  const { data } = await api.post<CreateSessionResponse>('/sessions', profile);
  return data;
}

export async function listSessions(): Promise<SessionsListResponse> {
  const { data } = await api.get<SessionsListResponse>('/sessions');
  return data;
}
