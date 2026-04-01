import React from 'react';
import { 
  ShoppingCart, 
  Users, 
  TrendingUp, 
  Zap, 
  ArrowUpRight,
  BarChart3
} from 'lucide-react';

const Analytics = () => {
  const metrics = [
    {
      title: "Total Orders",
      value: "1,284",
      change: "+12.5%",
      icon: <ShoppingCart className="w-5 h-5 text-[#0f6885]" />,
      description: "Orders successfully created by AI"
    },
    {
      title: "Active Leads",
      value: "432",
      change: "+8.2%",
      icon: <Users className="w-5 h-5 text-[#0f6885]" />,
      description: "Customers currently chatting"
    },
    {
      title: "Conversion Rate",
      value: "18.4%",
      change: "+2.1%",
      icon: <TrendingUp className="w-5 h-5 text-[#0f6885]" />,
      description: "Chats turned into orders"
    },
    {
      title: "Automation Rate",
      value: "94.2%",
      change: "+1.5%",
      icon: <Zap className="w-5 h-5 text-[#0f6885]" />,
      description: "Handled without human handoff"
    }
  ];

  return (
    <div className="max-w-6xl px-10">
      <div className="mb-8">
        <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Store Performance</h1>
        <p className="text-[15px] font-medium text-gray-400 mb-8">Track your AI agent's impact on business growth.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map((metric, index) => (
          <div key={index} className="bg-white border border-gray-100 shadow-sm rounded-2xl p-6 transition-all hover:shadow-md">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 bg-[#eef6f9] rounded-xl">
                {metric.icon}
              </div>
              <div className="flex items-center gap-1 text-green-500 bg-green-50 px-2 py-1 rounded-lg">
                <span className="text-xs font-bold">{metric.change}</span>
                <ArrowUpRight className="w-3 h-3" />
              </div>
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-400 mb-1">{metric.title}</h3>
              <div className="text-2xl font-extrabold text-gray-800 mb-1">{metric.value}</div>
              <p className="text-xs font-medium text-gray-400">{metric.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Chart Placeholder / Performance Breakdown */}
      <div className="bg-white border border-gray-100 shadow-sm rounded-2xl p-8 flex flex-col items-center justify-center min-h-[400px]">
        <div className="p-4 bg-gray-50 rounded-full mb-4">
          <BarChart3 className="w-12 h-12 text-gray-200" />
        </div>
        <h3 className="text-lg font-bold text-gray-800 mb-2">Detailed Analytics Coming Soon</h3>
        <p className="text-sm text-gray-400 font-medium text-center max-w-sm">
          We're finalizing the real-time data integration to provide more granular insights into your store's performance.
        </p>
      </div>
    </div>
  );
};

export default Analytics;
