import type { LucideIcon } from 'lucide-react';

export interface KpiData {
  label: string;
  value: string;
  delta: string;
  up: boolean;
  sub: string;
  icon: React.ReactNode;
  bg: string;
  text: string;
  sparkline: number[];
}

export interface HourlyData {
  h: string;
  v: number;
}

export interface PendingOrder {
  id: number;
  name: string;
  product: string;
  phone: string;
  address: string;
  platform: string;
  avatar: string;
}

export interface ActivityItem {
  id: number;
  Icon: LucideIcon;
  iconCls: string;
  text: string;
  time: string;
  state: string;
  cls: string;
}

export interface IntentData {
  intent: string;
  count: number;
  pct: number;
  color: string;
}

export interface ChannelData {
  name: string;
  count: number;
  pct: number;
  color: string;
}
