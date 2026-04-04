import React from 'react';
import { Activity } from 'lucide-react';
import { greeting, todayFormatted } from '../../utils/date';
import { KPI, HOURLY, PENDING_ORDERS, ACTIVITY, TOP_INTENTS, CHANNELS } from '../../constants/dashboard';
import KpiCard from '../../components/dashboard/KpiCard';
import ConversationVolume from '../../components/dashboard/ConversationVolume';
import PendingOrders from '../../components/dashboard/PendingOrders';
import RecentActivity from '../../components/dashboard/RecentActivity';
import AutomationCard from '../../components/dashboard/AutomationCard';
import IntentsChart from '../../components/dashboard/IntentsChart';
import ChannelsChart from '../../components/dashboard/ChannelsChart';

const Dashboard: React.FC = () => (
  <div className="h-full overflow-y-auto bg-gray-50 px-8 py-6">

    {/* Greeting */}
    <div className="flex items-center justify-between mb-7">
      <div>
        <h2 className="text-2xl font-extrabold text-gray-900">{greeting()}, Admin</h2>
        <p className="text-sm text-gray-400 mt-0.5 capitalize">{todayFormatted()}</p>
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

    {/* KPI Cards */}
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-7">
      {KPI.map((k) => <KpiCard key={k.label} k={k} />)}
    </div>

    {/* Main grid */}
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

      {/* Left col (span 2) */}
      <div className="xl:col-span-2 flex flex-col gap-6">
        <ConversationVolume data={HOURLY} total="81" />
        <PendingOrders orders={PENDING_ORDERS} />
        <RecentActivity items={ACTIVITY} />
      </div>

      {/* Right col */}
      <div className="flex flex-col gap-6">
        <AutomationCard />
        <IntentsChart intents={TOP_INTENTS} />
        <ChannelsChart channels={CHANNELS} />
      </div>
    </div>
  </div>
);

export default Dashboard;
