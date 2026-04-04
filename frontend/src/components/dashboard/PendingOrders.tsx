import React from 'react';
import { AlertCircle, CheckCircle, Package, Phone, MapPin } from 'lucide-react';
import type { PendingOrder } from '../../types';

interface PendingOrdersProps {
  orders: PendingOrder[];
}

const PendingOrders: React.FC<PendingOrdersProps> = ({ orders }) => (
  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
      <div className="flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-orange-500" />
        <h3 className="font-bold text-gray-800 text-sm">Orders Awaiting Confirmation</h3>
      </div>
      <span className="bg-orange-100 text-orange-600 text-xs font-bold rounded-full px-2.5 py-0.5">{orders.length}</span>
    </div>
    <div className="divide-y divide-gray-50">
      {orders.map((o) => (
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
);

export default PendingOrders;
