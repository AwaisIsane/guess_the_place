import type { Config, Coordinate, Game, GuessResult, Summary } from "./types";

export type GameState = {
  phase: "booting" | "landing" | "playing" | "result" | "summary";
  config: Config | null;
  game: Game | null;
  guess: Coordinate | null;
  result: GuessResult | null;
  summary: Summary | null;
  error: string;
};

export type GameAction =
  | { type: "READY"; config: Config }
  | { type: "GAME_STARTED"; game: Game }
  | { type: "GUESS_PLACED"; coordinate: Coordinate }
  | { type: "GUESS_SCORED"; result: GuessResult }
  | { type: "ROUND_ADVANCED"; game: Game }
  | { type: "GAME_COMPLETED"; summary: Summary }
  | { type: "FAILED"; message: string };

export const initialGameState: GameState = {
  phase: "booting", config: null, game: null, guess: null, result: null, summary: null, error: "",
};

export function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case "READY": return { ...state, phase: "landing", config: action.config };
    case "GAME_STARTED": return {
      ...state, phase: "playing", game: action.game, guess: null, result: null, summary: null, error: "",
    };
    case "GUESS_PLACED": return { ...state, guess: action.coordinate };
    case "GUESS_SCORED": return { ...state, phase: "result", result: action.result };
    case "ROUND_ADVANCED": return { ...state, phase: "playing", game: action.game, guess: null, result: null };
    case "GAME_COMPLETED": return { ...state, phase: "summary", game: null, summary: action.summary };
    case "FAILED": return { ...state, error: action.message };
  }
}
