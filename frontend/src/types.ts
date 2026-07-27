export type Config = {
  mapillary_client_token: string;
  map_style_url: string;
  map_attribution: string;
  rounds_per_game: number;
};

export type Game = {
  game_id: string;
  status: "active" | "complete";
  current_round: number;
  total_score: number;
  round: null | {
    number: number;
    image_id: string;
    sequence_id?: string;
    compass_angle?: number;
  };
};

export type GuessResult = {
  round: number;
  distance_km: number;
  score: number;
  total_score: number;
  guess: Coordinate;
  actual: Coordinate;
  game_complete: boolean;
};

export type Coordinate = { latitude: number; longitude: number };

export type Summary = {
  game_id: string;
  total_score: number;
  maximum_score: number;
  rounds: (GuessResult & { round: number })[];
};
