import type { Config, Coordinate, Game, GuessResult, Summary } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Something went wrong" }));
    throw new Error(body.detail ?? "Something went wrong");
  }
  return response.json();
}

export const api = {
  config: () => request<Config>("/api/v1/config"),
  createGame: () => request<Game>("/api/v1/games", { method: "POST" }),
  game: (id: string) => request<Game>(`/api/v1/games/${id}`),
  guess: (id: string, round: number, coordinate: Coordinate) =>
    request<GuessResult>(`/api/v1/games/${id}/rounds/${round}/guess`, {
      method: "POST",
      body: JSON.stringify(coordinate),
    }),
  summary: (id: string) => request<Summary>(`/api/v1/games/${id}/summary`),
};
