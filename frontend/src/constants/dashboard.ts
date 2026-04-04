import React from 'react';
import {
  ShoppingCart, Clock, Zap, MessageSquare,
  CheckCircle, AlertTriangle,
} from 'lucide-react';
import type { KpiData, HourlyData, PendingOrder, ActivityItem, IntentData, ChannelData } from '../types';

export const KPI: KpiData[] = [
  {
    label: 'Conversations', value: '81', delta: '+12', up: true, sub: 'vs Yesterday',
    icon: React.createElement(MessageSquare, { className: 'w-5 h-5' }),
    bg: 'bg-blue-50', text: 'text-blue-600', sparkline: [30, 45, 38, 60, 55, 72, 81],
  },
  {
    label: 'Orders Generated', value: '42', delta: '+8', up: true, sub: 'Rate: 52%',
    icon: React.createElement(ShoppingCart, { className: 'w-5 h-5' }),
    bg: 'bg-emerald-50', text: 'text-emerald-600', sparkline: [18, 22, 20, 30, 28, 35, 42],
  },
  {
    label: 'Awaiting Agent', value: '3', delta: '-2', up: false, sub: 'Active fallbacks',
    icon: React.createElement(Clock, { className: 'w-5 h-5' }),
    bg: 'bg-orange-50', text: 'text-orange-500', sparkline: [8, 5, 7, 4, 6, 5, 3],
  },
  {
    label: 'Automation Rate', value: '96%', delta: '+2%', up: true, sub: '4 fallbacks today',
    icon: React.createElement(Zap, { className: 'w-5 h-5' }),
    bg: 'bg-violet-50', text: 'text-violet-600', sparkline: [88, 90, 91, 93, 94, 95, 96],
  },
];

export const HOURLY: HourlyData[] = [
  { h: '08h', v: 4 }, { h: '09h', v: 9 }, { h: '10h', v: 14 }, { h: '11h', v: 11 },
  { h: '12h', v: 7 }, { h: '13h', v: 5 }, { h: '14h', v: 13 }, { h: '15h', v: 18 },
  { h: '16h', v: 15 }, { h: '17h', v: 8 }, { h: '18h', v: 3 }, { h: '19h', v: 2 },
];

export const PENDING_ORDERS: PendingOrder[] = [
  { id: 1, name: 'Alex', product: 'T-shirt Rouge M', phone: '+21612345678', address: 'Tunis', platform: 'WhatsApp', avatar: 'https://i.pravatar.cc/150?img=11' },
  { id: 2, name: 'Sarra', product: 'Jean Bleu L', phone: '+21698765432', address: 'Sfax', platform: 'Messenger', avatar: 'https://i.pravatar.cc/150?img=5' },
  { id: 3, name: 'Youssef', product: 'Veste Noire XL', phone: '+21655001122', address: 'Sousse', platform: 'WhatsApp', avatar: 'https://i.pravatar.cc/150?img=13' },
];

export const ACTIVITY: ActivityItem[] = [
  { id: 1, Icon: ShoppingCart, iconCls: 'bg-emerald-50 text-emerald-600', text: 'Alex ordered 2 red T-shirts M', time: '3 min', state: 'COMPLETED', cls: 'bg-green-50 text-green-700' },
  { id: 2, Icon: MessageSquare, iconCls: 'bg-yellow-50 text-yellow-600', text: 'Sarra is asking about delivery times', time: '8 min', state: 'WAITING', cls: 'bg-yellow-50 text-yellow-700' },
  { id: 3, Icon: AlertTriangle, iconCls: 'bg-red-50 text-red-500', text: 'Youssef — fallback triggered', time: '14 min', state: 'FALLBACK', cls: 'bg-red-50 text-red-600' },
  { id: 4, Icon: CheckCircle, iconCls: 'bg-emerald-50 text-emerald-600', text: 'Nour confirmed order #1042', time: '21 min', state: 'COMPLETED', cls: 'bg-green-50 text-green-700' },
  { id: 5, Icon: ShoppingCart, iconCls: 'bg-emerald-50 text-emerald-600', text: 'Amine ordered 1 black jacket XL', time: '35 min', state: 'COMPLETED', cls: 'bg-green-50 text-green-700' },
];

export const TOP_INTENTS: IntentData[] = [
  { intent: 'ORDER_PRODUCT', count: 42, pct: 52, color: 'bg-[#0f6885]' },
  { intent: 'ASK_SHIPPING', count: 18, pct: 22, color: 'bg-blue-400' },
  { intent: 'PRICE_INQUIRY', count: 12, pct: 15, color: 'bg-violet-400' },
  { intent: 'PRODUCT_INFO', count: 9, pct: 11, color: 'bg-orange-400' },
];

export const CHANNELS: ChannelData[] = [
  { name: 'WhatsApp', count: 53, pct: 65, color: 'bg-green-500' },
  { name: 'Messenger', count: 22, pct: 27, color: 'bg-blue-500' },
  { name: 'Instagram', count: 6, pct: 8, color: 'bg-purple-400' },
];
