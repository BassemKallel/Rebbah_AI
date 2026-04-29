/**
 * dashboardApi.ts — Client for all Dashboard KPI endpoints.
 */
import api from './axiosInstance';

const BASE = '/api/v1/crm/dashboard';

export interface KpisResponse {
  conversations:  { today: number; delta: number; up: boolean; sub: string; sparkline: number[] };
  orders:         { today: number; delta: number; up: boolean; conversion_rate: number; sub: string; sparkline: number[] };
  awaiting_agent: { count: number; delta: number; up: boolean; sub: string; sparkline: number[] };
  automation:     { rate: number; delta: number; up: boolean; fallbacks_today: number; sub: string; sparkline: number[] };
}

export interface HourlyPoint { h: string; v: number; }

export interface PendingOrderItem {
  id: number;
  name: string;
  product: string;
  phone: string;
  address: string;
  platform: string;
  avatar: string | null;
  pending_order_reference: string;
}

export interface ActivityItem {
  id: number;
  text: string;
  time: string;
  state: string;
  event_type: string;
  icon_cls: string;
  cls: string;
}

export interface IntentItem { intent: string; count: number; pct: number; color: string; }
export interface ChannelItem { name: string; count: number; pct: number; color: string; }

export const fetchKpis = (shopId: string): Promise<KpisResponse> =>
  api.get(`${BASE}/kpis/`, { params: { shop_id: shopId } }).then((r) => r.data);

export const fetchHourly = (shopId: string, date?: string): Promise<HourlyPoint[]> =>
  api.get(`${BASE}/hourly/`, { params: { shop_id: shopId, ...(date ? { date } : {}) } }).then((r) => r.data);

export const fetchPendingOrders = (shopId: string): Promise<PendingOrderItem[]> =>
  api.get(`${BASE}/pending-orders/`, { params: { shop_id: shopId } }).then((r) => r.data);

export const fetchRecentActivity = (shopId: string, limit = 10): Promise<ActivityItem[]> =>
  api.get(`${BASE}/recent-activity/`, { params: { shop_id: shopId, limit } }).then((r) => r.data);

export const fetchTopIntents = (shopId: string, date?: string): Promise<IntentItem[]> =>
  api.get(`${BASE}/top-intents/`, { params: { shop_id: shopId, ...(date ? { date } : {}) } }).then((r) => r.data);

export const fetchChannels = (shopId: string): Promise<ChannelItem[]> =>
  api.get(`${BASE}/channels/`, { params: { shop_id: shopId } }).then((r) => r.data);

export interface LeadFunnelStage {
  key: string;
  label: string;
  count: number;
  pct: number;
  color: string;
  color_hex: string;
  sparkline: number[];
}
export interface LeadFunnelResponse {
  stages: LeadFunnelStage[];
  conversion: { conv_to_lead: number; lead_to_qualified: number };
  total: number;
}

export const fetchLeadFunnel = (shopId: string): Promise<LeadFunnelResponse> =>
  api.get(`${BASE}/lead-funnel/`, { params: { shop_id: shopId } }).then((r) => r.data);
