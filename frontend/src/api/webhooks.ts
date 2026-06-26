import api from './client';

export interface WebhookConfig {
  registered: true;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
  last_triggered: string | null;
}

export interface WebhookRegistration {
  webhook_id: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
  webhook_secret: string;
}

export interface TestWebhookResult {
  delivered: boolean;
  status_code: number | null;
  error: string | null;
}

export async function registerWebhook(
  url: string,
  events: string[]
): Promise<WebhookRegistration> {
  const { data } = await api.post<WebhookRegistration>('/webhooks', { url, events });
  return data;
}

export async function getWebhook(): Promise<{ registered: false } | WebhookConfig> {
  const { data } = await api.get<{ registered: false } | WebhookConfig>('/webhooks');
  return data;
}

export async function deleteWebhook(): Promise<void> {
  await api.delete('/webhooks');
}

export async function testWebhook(): Promise<TestWebhookResult> {
  const { data } = await api.post<TestWebhookResult>('/webhooks/test');
  return data;
}
