import type { InvestigationProgressEvent } from "@/types";

type ProgressSubscription = () => void;

export async function subscribeToInvestigationProgress(
  investigationId: string,
  accessToken: string,
  onProgress: (event: InvestigationProgressEvent) => void,
): Promise<ProgressSubscription> {
  return new Promise<ProgressSubscription>((resolve, reject) => {
    const baseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const source = new EventSource(
      `${baseUrl}/investigate/progress/${investigationId}?token=${encodeURIComponent(
        accessToken,
      )}`,
    );

    source.onopen = () => {
      resolve(() => source.close());
    };

    source.onmessage = (messageEvent) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(messageEvent.data);
      } catch {
        return;
      }

      const event = parsed as Partial<InvestigationProgressEvent>;
      if (
        typeof event.stage !== "string" ||
        typeof event.message !== "string" ||
        (event.status !== "running" &&
          event.status !== "completed" &&
          event.status !== "error")
      ) {
        return;
      }

      onProgress({
        investigation_id: event.investigation_id ?? investigationId,
        stage: event.stage,
        status: event.status,
        message: event.message,
        timestamp: event.timestamp ?? new Date().toISOString(),
      });

      if (event.stage === "completed") {
        source.close();
      }
    };

    source.onerror = () => {
      source.close();
      reject(
        new Error(
          "The investigation progress stream is unavailable. The investigation will still continue.",
        ),
      );
    };
  });
}
