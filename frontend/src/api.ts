import type { Config, Coordinate, Game, GuessResult, Summary } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(url, {
    ...init,
    credentials: "same-origin",
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Something went wrong" }));
    throw new Error(body.detail ?? "Something went wrong");
  }
  return response.json();
}

const pendingKeys = new Map<string, string>();

export const api = {
  config: () => request<Config>("/api/v1/config"),
  createGame: () => request<Game>("/api/v1/games", { method: "POST" }),
  game: (id: string) => request<Game>(`/api/v1/games/${id}`),
  guess: async (id: string, round: number, coordinate: Coordinate) => {
    const operation = `${id}:${round}`;
    const key = pendingKeys.get(operation) ?? crypto.randomUUID();
    pendingKeys.set(operation, key);
    const result = await request<GuessResult>(`/api/v1/games/${id}/rounds/${round}/guess`, {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify(coordinate),
    });
    pendingKeys.delete(operation);
    return result;
  },
  summary: (id: string) => request<Summary>(`/api/v1/games/${id}/summary`),
};
