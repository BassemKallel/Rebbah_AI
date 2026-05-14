export interface BotConfiguration {
  id?: number;
  shop_id: string;
  shop_name: string;
  ai_agent_name: string;
  business_domain: string;
  target_audience: string;
  communication_tone: string;
  language_rules: string;
  delivery_policy: string;
  required_checkout_info: string;
  custom_intents?: Record<string, string>;
  bot_enabled: boolean;
}
