import type { Lead, LeadStatus, PlatformInfo, StatusConfig } from '../types';

export const getPlatformInfo = (platformId: string = ''): PlatformInfo => {
  const lower = platformId.toLowerCase();
  if (lower.startsWith('whatsapp'))
    return { label: 'WhatsApp', color: 'bg-green-100 text-green-700', dot: 'bg-green-500' };
  if (lower.startsWith('instagram'))
    return { label: 'Instagram', color: 'bg-pink-100 text-pink-700', dot: 'bg-pink-500' };
  if (lower.startsWith('messenger') || lower.startsWith('facebook'))
    return { label: 'Messenger', color: 'bg-blue-100 text-blue-700', dot: 'bg-blue-500' };
  return { label: platformId.split(':')[0] || '—', color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' };
};

export const getStatusValue = (lead: Lead): LeadStatus => {
  if (lead.agent_confirmation_pending) return 'agent';
  if (lead.has_pending_order) return 'pending';
  return 'confirmed';
};

export const getStatusConfig = (lead: Lead): StatusConfig => {
  const status = lead.lead_status;
  if (status === 'QUALIFIED')
    return { label: lead.agent_confirmation_pending ? 'Confirmation agent' : 'Qualifié', color: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-400' };
  if (status === 'ENGAGED')
    return { label: 'Engagé', color: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-400' };
  return { label: 'Prospect', color: 'bg-gray-50 text-gray-500 border-gray-200', dot: 'bg-gray-400' };
};

export const matchTab = (lead: Lead, tab: string): boolean => {
  if (tab === 'all') return true;
  if (tab === 'prospect') return lead.lead_status === 'PROSPECT';
  if (tab === 'engaged') return lead.lead_status === 'ENGAGED';
  if (tab === 'qualified') return lead.lead_status === 'QUALIFIED';
  // legacy tabs (rétro-compatibilité avec agent_confirmation_pending)
  if (tab === 'pending') return lead.has_pending_order && !lead.agent_confirmation_pending;
  if (tab === 'confirmed') return !lead.has_pending_order && !lead.agent_confirmation_pending;
  if (tab === 'agent') return !!lead.agent_confirmation_pending;
  return true;
};
