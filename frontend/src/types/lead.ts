export interface Lead {
  id: number;
  uuid: string;
  platform_id: string;
  name: string;
  shop_id: string;
  product_id: string | null;
  variation_id: string | null;
  color: string;
  size: string;
  quantity: number;
  address: string;
  phone_number: string;
  has_pending_order: boolean;
  pending_order_reference: string;
  pending_order_created_at: string | null;
  agent_confirmation_pending: boolean;
  created_at: string;
  updated_at: string;
}

export type LeadStatus = 'confirmed' | 'pending' | 'agent';

export interface StatusOption {
  value: LeadStatus;
  label: string;
  has_pending_order: boolean;
  agent_confirmation_pending: boolean;
}

export interface PlatformInfo {
  label: string;
  color: string;
  dot: string;
}

export interface StatusConfig {
  label: string;
  color: string;
  dot: string;
}
