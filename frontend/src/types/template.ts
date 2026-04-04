export type TemplateType =
  | 'response'
  | 'missing_entity'
  | 'out_of_stock'
  | 'order_confirmed'
  | 'disambiguation'
  | 'misc';

export interface ResponseTemplate {
  id: number;
  shop_id: string | null;
  language: 'FR' | 'AR' | 'EN';
  template_type: TemplateType;
  intent: string;
  text: string;
  available_variables: string[];
  is_default: boolean;
}
