// Shared in-memory state store for Next.js serverless functions
let globalState = null;
let lastTimestamp = 0;

export function setLatestState(state) {
  globalState = {
    ...state,
    received_at: new Date().toISOString(),
  };
  lastTimestamp = Date.now();
}

export function getLatestState() {
  return globalState;
}

export function getLastTimestamp() {
  return lastTimestamp;
}
