export interface BotConfiguration {
  id: number;
  shop_id: string;
  shop_name: string;
  language: 'AUTO' | 'FR' | 'AR' | 'EN';
  ai_agent_name: string;
  custom_intents: Record<string, string>;
}
