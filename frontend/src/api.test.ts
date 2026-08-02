import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

const result = {
  round: 1,
  distance_km: 12.5,
  score: 4800,
  total_score: 4800,
  guess: { latitude: 10, longitude: 20 },
  actual: { latitude: 11, longitude: 21 },
  game_complete: false,
};

function response(ok: boolean, body: unknown): Response {
  return { ok, json: vi.fn().mockResolvedValue(body) } as unknown as Response;
}

describe("api.guess", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("preserves JSON and idempotency headers", async () => {
    fetchMock.mockResolvedValue(response(true, result));

    await api.guess("game-with-headers", 1, result.guess);

    const [url, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(url).toBe("/api/v1/games/game-with-headers/rounds/1/guess");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Idempotency-Key")).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect(init).toMatchObject({
      method: "POST",
      credentials: "same-origin",
      body: JSON.stringify(result.guess),
    });
  });

  it("reuses a key after failure and clears it after success", async () => {
    fetchMock
      .mockResolvedValueOnce(response(false, { detail: "temporary failure" }))
      .mockResolvedValue(response(true, result));

    await expect(api.guess("retry-game", 2, result.guess)).rejects.toThrow("temporary failure");
    await api.guess("retry-game", 2, result.guess);
    await api.guess("retry-game", 2, result.guess);

    const keys = fetchMock.mock.calls.map(([, init]) =>
      new Headers(init?.headers).get("Idempotency-Key"),
    );
    expect(keys[1]).toBe(keys[0]);
    expect(keys[2]).not.toBe(keys[1]);
  });
});
