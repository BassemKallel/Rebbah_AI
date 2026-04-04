import { useQuery } from '@tanstack/react-query';
import { fetchConversations, fetchMessages } from '../api/crmApi';
import { SHOP_ID } from '../constants';

export const useConversations = () => {
  return useQuery({
    queryKey: ['conversations', SHOP_ID],
    queryFn: async () => {
      const { data } = await fetchConversations(SHOP_ID);
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });
};

export const useMessages = (convIds: number[]) => {
  return useQuery({
    queryKey: ['messages', convIds],
    queryFn: async () => {
      const results = await Promise.all(convIds.map((id) => fetchMessages(id)));
      const all = results.flatMap(({ data }) =>
        Array.isArray(data) ? data : (data.results ?? [])
      );
      // Deduplicate and sort chronologically
      const seen = new Set<string | number>();
      return all
        .filter((m) => {
          const key = m.id ?? `${m.created_at}-${m.text}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    },
    enabled: convIds.length > 0,
  });
};
