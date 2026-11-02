import { useQuery } from "@tanstack/react-query";

import { getStoredToken } from "@/lib/token";
import { getClusters } from "@/services/api";

export function useClusters(userId: string | undefined) {
  return useQuery({
    queryKey: ["clusters", userId],
    queryFn: async () => {
      const accessToken = getStoredToken();
      if (!accessToken) {
        throw new Error("Your session has expired. Please sign in again.");
      }
      return getClusters(accessToken);
    },
    enabled: Boolean(userId),
    staleTime: 30000,
  });
}
