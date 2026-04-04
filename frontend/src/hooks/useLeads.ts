import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchLeads, patchLead, deleteLead } from '../api/crmApi';
import { SHOP_ID } from '../constants';

export const useLeads = (page?: number) => {
  return useQuery({
    queryKey: ['leads', SHOP_ID, page],
    queryFn: async () => {
      const { data } = await fetchLeads(SHOP_ID);
      return {
        results: data.results || data,
        count: data.count || (data.results || data).length,
      };
    },
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      patchLead(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};

export const useDeleteLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteLead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};
