import { describe, expect, it } from "vitest";
import { gameReducer, initialGameState } from "./gameMachine";

describe("gameReducer", () => {
  it("moves from boot to landing when config loads", () => {
    const state = gameReducer(initialGameState, {
      type: "READY",
      config: { mapillary_client_token: "", map_style_url: "style", map_attribution: "map", rounds_per_game: 5 },
    });
    expect(state.phase).toBe("landing");
  });

  it("preserves the scored result as a distinct phase", () => {
    const result = {
      round: 1, distance_km: 10, score: 4900, total_score: 4900,
      guess: { latitude: 1, longitude: 2 }, actual: { latitude: 1.1, longitude: 2.1 },
      game_complete: false,
    };
    expect(gameReducer(initialGameState, { type: "GUESS_SCORED", result }).phase).toBe("result");
  });
});
