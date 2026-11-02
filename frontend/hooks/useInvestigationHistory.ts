import { useQuery } from "@tanstack/react-query";

import { getStoredToken } from "@/lib/token";
import { getInvestigationHistory } from "@/services/api";

export function useInvestigationHistory(userId: string | undefined) {
  return useQuery({
    queryKey: ["investigation-history", userId],
    queryFn: async () => {
      const accessToken = getStoredToken();
      if (!accessToken) {
        throw new Error("Your session has expired. Please sign in again.");
      }
      return getInvestigationHistory(accessToken);
    },
    enabled: Boolean(userId),
  });
}
