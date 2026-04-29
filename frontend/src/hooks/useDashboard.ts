import { useQuery } from '@tanstack/react-query';
import { getShopId } from '../providers/AuthProvider';
import {
  fetchKpis, fetchHourly, fetchPendingOrders,
  fetchRecentActivity, fetchTopIntents, fetchChannels,
  fetchLeadFunnel,
} from '../api/dashboardApi';

const staleTime = 60_000; // 1 minute

export const useKpis = () => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-kpis', shopId],
    queryFn: () => fetchKpis(shopId),
    enabled: !!shopId,
    staleTime,
  });
};

export const useHourly = (date?: string) => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-hourly', shopId, date],
    queryFn: () => fetchHourly(shopId, date),
    enabled: !!shopId,
    staleTime,
  });
};

export const usePendingOrders = () => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-pending-orders', shopId],
    queryFn: () => fetchPendingOrders(shopId),
    enabled: !!shopId,
    staleTime: 30_000,
  });
};

export const useRecentActivity = (limit = 10) => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-recent-activity', shopId, limit],
    queryFn: () => fetchRecentActivity(shopId, limit),
    enabled: !!shopId,
    staleTime: 30_000,
  });
};

export const useTopIntents = (date?: string) => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-top-intents', shopId, date],
    queryFn: () => fetchTopIntents(shopId, date),
    enabled: !!shopId,
    staleTime,
  });
};

export const useChannels = () => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-channels', shopId],
    queryFn: () => fetchChannels(shopId),
    enabled: !!shopId,
    staleTime,
  });
};

export const useLeadFunnel = () => {
  const shopId = getShopId() ?? '';
  return useQuery({
    queryKey: ['dashboard-lead-funnel', shopId],
    queryFn: () => fetchLeadFunnel(shopId),
    enabled: !!shopId,
    staleTime: 60_000,
  });
};
