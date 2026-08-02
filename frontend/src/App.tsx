import { lazy, Suspense, useCallback, useEffect, useReducer, useState } from "react";
import { api } from "./api";
import { gameReducer, initialGameState } from "./gameMachine";
import type { Config, Coordinate, GuessResult, Summary } from "./types";

const GuessMap = lazy(() => import("./GuessMap").then((module) => ({ default: module.GuessMap })));
const MapillaryView = lazy(() => import("./MapillaryView").then((module) => ({ default: module.MapillaryView })));
const SAVED_GAME = "worldguessr.activeGame";

export default function App() {
  const [state, dispatch] = useReducer(gameReducer, initialGameState);
  const { config, game, guess, result, summary, error } = state;
  const [mapOpen, setMapOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.config()
      .then(async (loadedConfig) => {
        dispatch({ type: "READY", config: loadedConfig });
        const id = localStorage.getItem(SAVED_GAME);
        if (!id) return;
        try {
          const saved = await api.game(id);
          if (
            loadedConfig.mapillary_client_token
            && saved.round?.image_id.startsWith("demo-")
          ) {
            localStorage.removeItem(SAVED_GAME);
            return;
          }
          if (saved.status === "complete") {
            return api.summary(id).then((loaded) =>
              dispatch({ type: "GAME_COMPLETED", summary: loaded }),
            );
          }
          dispatch({ type: "GAME_STARTED", game: saved });
        } catch {
          localStorage.removeItem(SAVED_GAME);
        }
      })
      .catch((e) => dispatch({ type: "FAILED", message: e.message }));
  }, []);

  const choose = useCallback(
    (coordinate: Coordinate) => dispatch({ type: "GUESS_PLACED", coordinate }),
    [],
  );

  async function start() {
    setBusy(true);
    try {
      const created = await api.createGame();
      dispatch({ type: "GAME_STARTED", game: created });
      localStorage.setItem(SAVED_GAME, created.game_id);
    } catch (e) {
      dispatch({
        type: "FAILED",
        message: e instanceof Error ? e.message : "Could not start a game",
      });
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!game?.round || !guess) return;
    setBusy(true);
    try {
      dispatch({
        type: "GUESS_SCORED",
        result: await api.guess(game.game_id, game.round.number, guess),
      });
      setMapOpen(false);
    } catch (e) {
      dispatch({
        type: "FAILED",
        message: e instanceof Error ? e.message : "Could not submit guess",
      });
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    if (!game || !result) return;
    if (result.game_complete) {
      dispatch({ type: "GAME_COMPLETED", summary: await api.summary(game.game_id) });
    } else {
      dispatch({ type: "ROUND_ADVANCED", game: await api.game(game.game_id) });
    }
    setMapOpen(false);
  }

  if (!config) return <main className="loading">Loading the world…</main>;
  if (summary) return <Final summary={summary} start={start} busy={busy} />;
  if (!game?.round) return <Landing start={start} busy={busy} error={error} />;
  if (result) return <RoundResult result={result} config={config} advance={advance} />;

  return (
    <main className="game-screen">
      <Suspense fallback={<div className="loading" role="status">Loading street view…</div>}>
        <MapillaryView imageId={game.round.image_id} accessToken={config.mapillary_client_token} />
      </Suspense>
      <header className="hud">
        <div className="brand-mini"><span>W</span> WorldGuessr</div>
        <div className="progress">
          <strong>Round {game.current_round}</strong><span> / 5</span>
          <div className="dots">
            {[1, 2, 3, 4, 5].map((n) => <i key={n} className={n <= game.current_round ? "on" : ""} />)}
          </div>
        </div>
        <div className="score"><small>Score</small>{game.total_score.toLocaleString()}</div>
      </header>
      <section className={`map-panel ${mapOpen ? "open" : ""}`}>
        <button className="map-toggle" onClick={() => setMapOpen(!mapOpen)}>
          {mapOpen ? "Close map" : "Place your guess"}
        </button>
        <Suspense fallback={<div className="loading" role="status">Loading map…</div>}>
          <GuessMap styleUrl={config.map_style_url} value={guess} onChange={choose} />
        </Suspense>
        <button className="primary guess-button" disabled={!guess || busy} onClick={submit}>
          {guess ? "Lock in guess" : "Choose a location"}
        </button>
      </section>
      {error && <div className="toast" role="alert" aria-live="assertive">{error}</div>}
    </main>
  );
}

function Landing({ start, busy, error }: { start: () => void; busy: boolean; error: string }) {
  return (
    <main className="landing">
      <nav><div className="brand"><span>W</span> WorldGuessr</div><a href="#how">How to play</a></nav>
      <section className="hero">
        <div className="eyebrow">A five-round world adventure</div>
        <h1>How well do you<br /><em>know the world?</em></h1>
        <p>Drop into a mystery street. Look around, follow the clues, and pinpoint where you are.</p>
        <button className="primary play" onClick={start} disabled={busy}>
          {busy ? "Finding somewhere…" : "Explore the world"} <b>→</b>
        </button>
        {error && <p className="error">{error}</p>}
        <div className="features">
          <div><b>5</b><span>Rounds</span></div>
          <div><b>25K</b><span>Max score</span></div>
          <div><b>∞</b><span>Time to explore</span></div>
        </div>
      </section>
      <section id="how" className="how">
        <article><b>01</b><h3>Explore</h3><p>Move through real street-level imagery and hunt for clues.</p></article>
        <article><b>02</b><h3>Pinpoint</h3><p>Open the world map and place your best guess.</p></article>
        <article><b>03</b><h3>Score</h3><p>The closer your pin, the more points you earn.</p></article>
      </section>
      <footer>Imagery by <a href="https://www.mapillary.com/">Mapillary</a> · Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a></footer>
    </main>
  );
}

function RoundResult({ result, config, advance }: { result: GuessResult; config: Config; advance: () => void }) {
  return (
    <main className="result-screen">
      <div className="result-map"><Suspense fallback={<div role="status">Loading result map…</div>}><GuessMap styleUrl={config.map_style_url} value={result.guess} result={result} interactive={false} /></Suspense></div>
      <section className="result-card">
        <div className="eyebrow">Round {result.round} complete</div>
        <h2>{result.score.toLocaleString()} <small>points</small></h2>
        <p>You were <strong>{formatDistance(result.distance_km)}</strong> from the location.</p>
        <div className="coordinates">
          <span>Guess<br /><b>{result.guess.latitude.toFixed(4)}, {result.guess.longitude.toFixed(4)}</b></span>
          <span>Location<br /><b>{result.actual.latitude.toFixed(4)}, {result.actual.longitude.toFixed(4)}</b></span>
        </div>
        <div className="running">Total score <strong>{result.total_score.toLocaleString()}</strong></div>
        <button className="primary" onClick={advance}>{result.game_complete ? "See final score" : "Next round"} →</button>
      </section>
    </main>
  );
}

function Final({ summary, start, busy }: { summary: Summary; start: () => void; busy: boolean }) {
  const percent = Math.round((summary.total_score / summary.maximum_score) * 100);
  return (
    <main className="final-screen">
      <div className="confetti">✦</div>
      <div className="eyebrow">Journey complete</div>
      <h1>{summary.total_score.toLocaleString()}</h1>
      <p>out of {summary.maximum_score.toLocaleString()} points · {percent}%</p>
      <section className="round-grid">
        {summary.rounds.map((r) => (
          <article key={r.round}><small>Round {r.round}</small><b>{r.score?.toLocaleString()}</b><span>{formatDistance(r.distance_km)} away</span></article>
        ))}
      </section>
      <button className="primary play" onClick={start} disabled={busy}>Play again →</button>
    </main>
  );
}

function formatDistance(km: number) {
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toLocaleString(undefined, { maximumFractionDigits: 1 })} km`;
}
