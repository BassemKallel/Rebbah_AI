import type { StatusOption, LeadStatus } from '../types';

export const STATUS_OPTIONS: StatusOption[] = [
  { value: 'confirmed', label: 'Confirmé', has_pending_order: false, agent_confirmation_pending: false },
  { value: 'pending', label: 'En attente', has_pending_order: true, agent_confirmation_pending: false },
  { value: 'agent', label: 'Confirmation agent', has_pending_order: true, agent_confirmation_pending: true },
];

export const STATUS_COLORS: Record<LeadStatus, { pill: string; dot: string; hover: string }> = {
  confirmed: { pill: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-400', hover: 'hover:bg-emerald-100' },
  pending: { pill: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-400', hover: 'hover:bg-amber-100' },
  agent: { pill: 'bg-orange-50 text-orange-700 border-orange-200', dot: 'bg-orange-400', hover: 'hover:bg-orange-100' },
};

export interface TabDef {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}
