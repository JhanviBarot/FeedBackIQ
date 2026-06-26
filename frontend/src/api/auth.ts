import api from './client';
import type { TokenResponse, UserMeResponse, ProfileData, HistoryResponse } from '../types/api';

export async function signup(fullName: string, email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/signup', { full_name: fullName, email, password });
  return data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);
  const { data } = await api.post<TokenResponse>('/auth/login', params);
  return data;
}

export function logout(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_data');
}

export async function getMe(): Promise<UserMeResponse> {
  const { data } = await api.get<UserMeResponse>('/auth/me');
  return data;
}

export async function updateProfile(profile: ProfileData): Promise<ProfileData> {
  const { data } = await api.put<ProfileData>('/auth/profile', profile);
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword });
}

export async function getHistory(): Promise<HistoryResponse> {
  const { data } = await api.get<HistoryResponse>('/auth/history');
  return data;
}
