import React from 'react';
import { Activity, ShoppingCart, MessageSquare, Clock, Zap } from 'lucide-react';
import { greeting, todayFormatted } from '../../utils/date';
import KpiCard from '../../components/dashboard/KpiCard';
import ConversationVolume from '../../components/dashboard/ConversationVolume';
import PendingOrders from '../../components/dashboard/PendingOrders';
import LeadFunnel from '../../components/dashboard/LeadFunnel';
import AutomationCard from '../../components/dashboard/AutomationCard';
import IntentsChart from '../../components/dashboard/IntentsChart';
import ChannelsChart from '../../components/dashboard/ChannelsChart';
import {
  useKpis, useHourly, usePendingOrders,
  useTopIntents, useChannels, useLeadFunnel,
} from '../../hooks/useDashboard';
import type { KpiData } from '../../types';

const Dashboard: React.FC = () => {
  const { data: kpisData } = useKpis();
  const { data: hourlyData } = useHourly();
  const { data: pendingData } = usePendingOrders();
  const { data: intentsData } = useTopIntents();
  const { data: channelsData } = useChannels();
  const { data: funnelData } = useLeadFunnel();

  // Build KPI cards from API response
  const kpiCards: KpiData[] = kpisData
    ? [
        {
          label: 'Conversations (7j)', value: String(kpisData.conversations.today),
          delta: (kpisData.conversations.delta >= 0 ? '+' : '') + kpisData.conversations.delta,
          up: kpisData.conversations.up, sub: kpisData.conversations.sub,
          icon: <MessageSquare className="w-5 h-5" />,
          bg: 'bg-blue-50', text: 'text-blue-600', sparkline: kpisData.conversations.sparkline,
        },
        {
          label: 'Commandes (7j)', value: String(kpisData.orders.today),
          delta: (kpisData.orders.delta >= 0 ? '+' : '') + kpisData.orders.delta,
          up: kpisData.orders.up, sub: kpisData.orders.sub,
          icon: <ShoppingCart className="w-5 h-5" />,
          bg: 'bg-emerald-50', text: 'text-emerald-600', sparkline: kpisData.orders.sparkline,
        },
        {
          label: 'Awaiting Agent', value: String(kpisData.awaiting_agent.count),
          delta: (kpisData.awaiting_agent.delta >= 0 ? '+' : '') + kpisData.awaiting_agent.delta,
          up: kpisData.awaiting_agent.up, sub: kpisData.awaiting_agent.sub,
          icon: <Clock className="w-5 h-5" />,
          bg: 'bg-orange-50', text: 'text-orange-500', sparkline: kpisData.awaiting_agent.sparkline,
        },
        {
          label: 'Automation Rate', value: `${kpisData.automation.rate}%`,
          delta: (kpisData.automation.delta >= 0 ? '+' : '') + kpisData.automation.delta + '%',
          up: kpisData.automation.up, sub: kpisData.automation.sub,
          icon: <Zap className="w-5 h-5" />,
          bg: 'bg-violet-50', text: 'text-violet-600', sparkline: kpisData.automation.sparkline,
        },
      ]
    : [];

  const automationRate = kpisData?.automation.rate ?? 0;
  const totalConversations = kpisData?.conversations.today ?? 0;
  const totalOrders = kpisData?.orders.today ?? 0;

  return (
    <div className="min-h-full bg-gray-50 px-4 sm:px-6 lg:px-8 py-5 sm:py-6 pb-8">

      {/* Greeting */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 sm:mb-7">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-gray-900">{greeting()}, Admin</h2>
          <p className="text-sm text-gray-400 mt-0.5 capitalize">{todayFormatted()}</p>
        </div>
        <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-white border border-gray-200 rounded-xl shadow-sm flex-shrink-0">
          <Activity className="w-4 h-4 text-emerald-500" />
          <span className="text-sm font-medium text-gray-700 hidden xs:inline">Bot Status</span>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Active
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5 mb-6 sm:mb-7">
        {kpiCards.map((k) => <KpiCard key={k.label} k={k} />)}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 sm:gap-6">

        {/* Left col (span 2) */}
        <div className="xl:col-span-2 flex flex-col gap-5 sm:gap-6">
          <ConversationVolume data={hourlyData ?? []} total={String(totalConversations)} />
          <PendingOrders orders={pendingData ?? []} />
          <LeadFunnel
            stages={funnelData?.stages ?? []}
            conversion={funnelData?.conversion ?? { conv_to_lead: 0, lead_to_qualified: 0 }}
            total={funnelData?.total ?? 0}
          />
        </div>

        {/* Right col */}
        <div className="flex flex-col gap-5 sm:gap-6">
          <AutomationCard
            rate={automationRate}
            conversations={totalConversations}
            orders={totalOrders}
            fallbacks={kpisData?.automation.fallbacks_today ?? 0}
          />
          <IntentsChart intents={intentsData ?? []} />
          <ChannelsChart channels={channelsData ?? []} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
