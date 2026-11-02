import { useMutation, useQueryClient } from "@tanstack/react-query";

import { investigateCluster } from "@/services/api";

export function useInvestigate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: investigateCluster,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["investigation-history"],
      });
    },
  });
}
