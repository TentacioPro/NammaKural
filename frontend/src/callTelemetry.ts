export interface TurnMeasurement {
  callId: string;
  turnId: string;
  modality: "voice" | "text" | "gps";
  submittedAt?: number;
  speechEndedAt?: number;
  endpointWaitMs?: number;
  browserSttMs?: number;
}

export function turnHeaders(turn?: TurnMeasurement) {
  return turn ? { "X-NK-Call-ID": turn.callId, "X-NK-Turn-ID": turn.turnId } : undefined;
}

export function recordBrowserMeasurement(
  kind: "call.started" | "call.ended" | "call.playback" | "call.upload",
  callId: string,
  turn?: TurnMeasurement,
  values?: Record<string, number | undefined>,
) {
  void fetch("/api/telemetry/browser", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, call_id: callId, turn_id: turn?.turnId, modality: turn?.modality, ...values }),
    keepalive: true,
  }).catch(() => undefined);
}
