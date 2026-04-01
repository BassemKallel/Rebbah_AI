import React from 'react';
import {
  ShoppingCart, Clock, Zap, TrendingUp,
  Users, CheckCircle, AlertCircle, AlertTriangle,
  ArrowRight, Bot, Package, MapPin, Phone, MessageSquare,
  ArrowUpRight, ArrowDownRight, Activity,
} from 'lucide-react';

/* ─── helpers ────────────────────────────────────────────────────── */
const today = new Date().toLocaleDateString('en-US', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
});
const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning';
  if (h < 18) return 'Good Afternoon';
  return 'Good Evening';
};

/* ─── KPI data ───────────────────────────────────────────────────── */
const KPI = [
  {
    label: 'Conversations',
    value: '81',
    delta: '+12',
    up: true,
    sub: 'vs Yesterday',
    icon: <MessageSquare className="w-5 h-5" />,
    bg: 'bg-blue-50',
    text: 'text-blue-600',
    sparkline: [30, 45, 38, 60, 55, 72, 81],
  },
  {
    label: 'Orders Generated',
    value: '42',
    delta: '+8',
    up: true,
    sub: 'Rate: 52%',
    icon: <ShoppingCart className="w-5 h-5" />,
    bg: 'bg-emerald-50',
    text: 'text-emerald-600',
    sparkline: [18, 22, 20, 30, 28, 35, 42],
  },
  {
    label: 'Awaiting Agent',
    value: '3',
    delta: '-2',
    up: false,
    sub: 'Active fallbacks',
    icon: <Clock className="w-5 h-5" />,
    bg: 'bg-orange-50',
    text: 'text-orange-500',
    sparkline: [8, 5, 7, 4, 6, 5, 3],
  },
  {
    label: 'Automation Rate',
    value: '96%',
    delta: '+2%',
    up: true,
    sub: '4 fallbacks today',
    icon: <Zap className="w-5 h-5" />,
    bg: 'bg-violet-50',
    text: 'text-violet-600',
    sparkline: [88, 90, 91, 93, 94, 95, 96],
  },
];

/* ─── Sparkline ──────────────────────────────────────────────────── */
const Sparkline = ({ data, up }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const H = 32;
  const W = 56;
  const step = W / (data.length - 1);
  const pts = data
    .map((v, i) => `${i * step},${H - ((v - min) / range) * H}`)
    .join(' ');
  return (
    <svg width={W} height={H} className="opacity-60">
      <polyline
        points={pts}
        fill="none"
        stroke={up ? '#10b981' : '#f97316'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

/* ─── KPI card ───────────────────────────────────────────────────── */
const KpiCard = ({ k }) => (
  <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex flex-col gap-4 hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between">
      <div className={`w-10 h-10 rounded-xl ${k.bg} ${k.text} flex items-center justify-center`}>
        {k.icon}
      </div>
      <Sparkline data={k.sparkline} up={k.up} />
    </div>
    <div>
      <p className="text-xs text-gray-500 font-medium">{k.label}</p>
      <p className="text-3xl font-extrabold text-gray-900 mt-0.5 tracking-tight">{k.value}</p>
    </div>
    <div className="flex items-center gap-1.5">
      <span className={`flex items-center gap-0.5 text-xs font-bold ${k.up ? 'text-emerald-600' : 'text-orange-500'}`}>
        {k.up
          ? <ArrowUpRight className="w-3.5 h-3.5" />
          : <ArrowDownRight className="w-3.5 h-3.5" />}
        {k.delta}
      </span>
      <span className="text-xs text-gray-400">{k.sub}</span>
    </div>
  </div>
);

/* ─── Hourly bar chart data ──────────────────────────────────────── */
const HOURLY = [
  { h: '08h', v: 4 }, { h: '09h', v: 9 }, { h: '10h', v: 14 }, { h: '11h', v: 11 },
  { h: '12h', v: 7 }, { h: '13h', v: 5 }, { h: '14h', v: 13 }, { h: '15h', v: 18 },
  { h: '16h', v: 15 }, { h: '17h', v: 8 }, { h: '18h', v: 3 }, { h: '19h', v: 2 },
];
const maxH = Math.max(...HOURLY.map((h) => h.v));

/* ─── Static lists ───────────────────────────────────────────────── */
const PENDING_ORDERS = [
  { id: 1, name: 'Alex',    product: 'T-shirt Rouge M', phone: '+21612345678', address: 'Tunis',  platform: 'WhatsApp',  avatar: 'https://i.pravatar.cc/150?img=11' },
  { id: 2, name: 'Sarra',   product: 'Jean Bleu L',     phone: '+21698765432', address: 'Sfax',   platform: 'Messenger', avatar: 'https://i.pravatar.cc/150?img=5' },
  { id: 3, name: 'Youssef', product: 'Veste Noire XL',  phone: '+21655001122', address: 'Sousse', platform: 'WhatsApp',  avatar: 'https://i.pravatar.cc/150?img=13' },
];

const ACTIVITY = [
  { id: 1, Icon: ShoppingCart, iconCls: 'bg-emerald-50 text-emerald-600', text: 'Alex ordered 2 red T-shirts M',    time: '3 min',  state: 'COMPLETED',  cls: 'bg-green-50 text-green-700' },
  { id: 2, Icon: MessageSquare, iconCls: 'bg-yellow-50 text-yellow-600',  text: 'Sarra is asking about delivery times', time: '8 min',  state: 'WAITING', cls: 'bg-yellow-50 text-yellow-700' },
  { id: 3, Icon: AlertTriangle, iconCls: 'bg-red-50 text-red-500',        text: 'Youssef — fallback triggered',             time: '14 min', state: 'FALLBACK',   cls: 'bg-red-50 text-red-600' },
  { id: 4, Icon: CheckCircle,   iconCls: 'bg-emerald-50 text-emerald-600',text: 'Nour confirmed order #1042',     time: '21 min', state: 'COMPLETED',  cls: 'bg-green-50 text-green-700' },
  { id: 5, Icon: ShoppingCart,  iconCls: 'bg-emerald-50 text-emerald-600',text: 'Amine ordered 1 black jacket XL',     time: '35 min', state: 'COMPLETED',  cls: 'bg-green-50 text-green-700' },
];

const TOP_INTENTS = [
  { intent: 'ORDER_PRODUCT',  count: 42, pct: 52, color: 'bg-[#0f6885]' },
  { intent: 'ASK_SHIPPING',   count: 18, pct: 22, color: 'bg-blue-400' },
  { intent: 'PRICE_INQUIRY',  count: 12, pct: 15, color: 'bg-violet-400' },
  { intent: 'PRODUCT_INFO',   count:  9, pct: 11, color: 'bg-orange-400' },
];

const CHANNELS = [
  { name: 'WhatsApp',  count: 53, pct: 65, color: 'bg-green-500' },
  { name: 'Messenger', count: 22, pct: 27, color: 'bg-blue-500' },
  { name: 'Instagram',       count:  6, pct:  8, color: 'bg-purple-400' },
];

/* ─── Dashboard ─────────────────────────────────────────────────── */
const Dashboard = () => (
  <div className="h-full overflow-y-auto bg-gray-50 px-8 py-6">

    {/* ── Greeting ── */}
    <div className="flex items-center justify-between mb-7">
      <div>
        <h2 className="text-2xl font-extrabold text-gray-900">{greeting()}, Admin</h2>
        <p className="text-sm text-gray-400 mt-0.5 capitalize">{today}</p>
      </div>
      <div className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl shadow-sm">
        <Activity className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium text-gray-700">Bot Status</span>
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Active
        </span>
      </div>
    </div>

    {/* ── KPI Cards ── */}
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-7">
      {KPI.map((k) => <KpiCard key={k.label} k={k} />)}
    </div>

    {/* ── Main grid ── */}
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

      {/* ── Left col (span 2) ── */}
      <div className="xl:col-span-2 flex flex-col gap-6">

        {/* Conversation Volume */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="font-bold text-gray-800 text-sm">Conversation Volume</h3>
              <p className="text-xs text-gray-400">Today — hourly breakdown</p>
            </div>
            <span className="text-xs bg-[#eef6f9] text-[#0f6885] font-semibold px-2.5 py-1 rounded-lg">81 Total</span>
          </div>
          <div className="flex items-end gap-1.5 h-24">
            {HOURLY.map((item) => (
              <div key={item.h} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t-md bg-[#0f6885]/80 hover:bg-[#0f6885] transition-colors cursor-default"
                  style={{ height: `${(item.v / maxH) * 80}px` }}
                  title={`${item.v} conv.`}
                />
                <span className="text-[9px] text-gray-400">{item.h}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Orders to confirm */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-orange-500" />
              <h3 className="font-bold text-gray-800 text-sm">Orders Awaiting Confirmation</h3>
            </div>
            <span className="bg-orange-100 text-orange-600 text-xs font-bold rounded-full px-2.5 py-0.5">{PENDING_ORDERS.length}</span>
          </div>
          <div className="divide-y divide-gray-50">
            {PENDING_ORDERS.map((o) => (
              <div key={o.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-gray-50 transition-colors">
                <img src={o.avatar} alt={o.name} className="w-9 h-9 rounded-full object-cover flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-800">{o.name}</p>
                  <div className="flex flex-wrap gap-3 mt-0.5">
                    <span className="flex items-center gap-1 text-xs text-gray-500"><Package className="w-3 h-3" />{o.product}</span>
                    <span className="flex items-center gap-1 text-xs text-gray-500"><Phone className="w-3 h-3" />{o.phone}</span>
                    <span className="flex items-center gap-1 text-xs text-gray-500"><MapPin className="w-3 h-3" />{o.address}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-[11px] bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">{o.platform}</span>
                  <button className="flex items-center gap-1 px-3 py-1.5 bg-[#0f6885] text-white text-xs font-semibold rounded-lg hover:bg-[#0c5973] transition-colors shadow-sm">
                    <CheckCircle className="w-3.5 h-3.5" /> Confirm
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent activity */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#0f6885]" />
              <h3 className="font-bold text-gray-800 text-sm">Recent Activity</h3>
            </div>
            <a href="/analytics" className="flex items-center gap-1 text-xs text-[#0f6885] font-semibold hover:underline">
              View All <ArrowRight className="w-3 h-3" />
            </a>
          </div>
          <div className="divide-y divide-gray-50">
            {ACTIVITY.map((item) => (
              <div key={item.id} className="flex items-center gap-4 px-6 py-3 hover:bg-gray-50 transition-colors">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${item.iconCls}`}>
                  <item.Icon className="w-4 h-4" />
                </div>
                <p className="flex-1 text-sm text-gray-700">{item.text}</p>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${item.cls}`}>{item.state}</span>
                  <span className="text-[11px] text-gray-400 whitespace-nowrap">{item.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right col ── */}
      <div className="flex flex-col gap-6">

        {/* Automatisation ring */}
        <div className="bg-gradient-to-br from-[#0f6885] to-[#0a4f66] rounded-2xl p-6 text-white shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-white/80" />
            <p className="text-sm font-semibold text-white/80">Automation</p>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <p className="text-5xl font-extrabold tracking-tight">96<span className="text-2xl text-white/70">%</span></p>
              <p className="text-xs text-white/60 mt-1">4 human interventions</p>
            </div>
            <div className="relative w-16 h-16">
              <svg viewBox="0 0 36 36" className="rotate-[-90deg] w-full h-full">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="3" />
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="white" strokeWidth="3"
                  strokeDasharray="96 4" strokeLinecap="round" />
              </svg>
              <p className="absolute inset-0 flex items-center justify-center text-[10px] font-bold">96%</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-white/20 grid grid-cols-2 gap-3">
            <div>
              <p className="text-2xl font-bold">81</p>
              <p className="text-[11px] text-white/60">Conversations</p>
            </div>
            <div>
              <p className="text-2xl font-bold">42</p>
              <p className="text-[11px] text-white/60">Orders</p>
            </div>
          </div>
        </div>

        {/* Top intents */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
            <Bot className="w-4 h-4 text-[#0f6885]" />
            <h3 className="font-bold text-gray-800 text-sm">Frequent Intents</h3>
          </div>
          <div className="px-6 py-4 space-y-4">
            {TOP_INTENTS.map((item) => (
              <div key={item.intent}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium text-gray-700">{item.intent}</span>
                  <span className="text-xs font-bold text-gray-500">{item.count}</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${item.color} transition-all`} style={{ width: `${item.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Channels */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
            <Users className="w-4 h-4 text-[#0f6885]" />
            <h3 className="font-bold text-gray-800 text-sm">Channels</h3>
          </div>
          <div className="px-6 py-4 space-y-4">
            {CHANNELS.map((c) => (
              <div key={c.name}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium text-gray-700">{c.name}</span>
                  <span className="text-xs font-bold text-gray-500">{c.count} conv.</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  </div>
);

export default Dashboard;
