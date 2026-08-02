import { useEffect, useRef, useState } from "react";
import { CancelMapillaryError, Viewer } from "mapillary-js";
import "mapillary-js/dist/mapillary.css";

type Props = { imageId: string; accessToken: string };
const LOAD_ERROR = "This Mapillary image could not be loaded. Check the image ID and client token.";
const WEBGL_ERROR = "Street view lost its graphics context. Retry to reload the imagery.";

export function MapillaryView({ imageId, accessToken }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const activeImageId = useRef(imageId);
  const lifecycle = useRef(0);
  const navigation = useRef(0);
  const recoveryAttempts = useRef(0);
  const [loadError, setLoadError] = useState("");
  const [viewerRevision, setViewerRevision] = useState(0);
  const isDemo = imageId.startsWith("demo-") || !accessToken;

  activeImageId.current = imageId;

  function retry() {
    recoveryAttempts.current = 0;
    setLoadError("");
    setViewerRevision((value) => value + 1);
  }

  useEffect(() => {
    if (!host.current || isDemo) return;
    const container = host.current;
    const lifecycleId = ++lifecycle.current;
    let disposed = false;
    let instance: Viewer | null = null;
    let recoveryTimer: number | undefined;

    const isCurrent = () => !disposed && lifecycle.current === lifecycleId;

    const moveTo = (targetImageId: string) => {
      if (!instance || !isCurrent()) return;
      const navigationId = ++navigation.current;
      setLoadError("");
      void instance.moveTo(targetImageId).then(
        () => {
          if (!isCurrent() || navigation.current !== navigationId) return;
          recoveryAttempts.current = 0;
        },
        (error: unknown) => {
          const stale = !isCurrent() || navigation.current !== navigationId;
          if (stale) return;
          if (error instanceof CancelMapillaryError) {
            console.error("Mapillary image navigation was cancelled", error);
          } else {
            console.error("Mapillary image failed to load", error);
          }
          setLoadError(LOAD_ERROR);
        },
      );
    };

    const removeViewer = () => {
      container.removeEventListener("webglcontextlost", handleContextLost, true);
      navigation.current += 1;
      if (viewer.current === instance) viewer.current = null;
      const removed = instance;
      instance = null;
      removed?.remove();
      container.replaceChildren();
    };

    const handleContextLost = (event: Event) => {
      if (!isCurrent()) return;
      event.preventDefault();
      removeViewer();
      if (recoveryAttempts.current >= 1) {
        setLoadError(WEBGL_ERROR);
        return;
      }
      recoveryAttempts.current += 1;
      recoveryTimer = window.setTimeout(() => {
        if (isCurrent()) setViewerRevision((value) => value + 1);
      }, 100);
    };

    setLoadError("");
    // React Strict Mode immediately cleans up the first development-only effect run.
    // Deferring construction prevents Mapillary from starting a request that cleanup aborts.
    queueMicrotask(() => {
      if (!isCurrent()) return;
      container.replaceChildren();
      instance = new Viewer({
        accessToken,
        container,
        component: { cover: false, sequence: true },
      });
      viewer.current = instance;
      container.addEventListener("webglcontextlost", handleContextLost, true);
      moveTo(activeImageId.current);
    });

    return () => {
      disposed = true;
      if (recoveryTimer !== undefined) window.clearTimeout(recoveryTimer);
      removeViewer();
    };
  }, [accessToken, isDemo, viewerRevision]);

  useEffect(() => {
    if (!viewer.current || !accessToken || imageId.startsWith("demo-")) return;
    const navigationId = ++navigation.current;
    const currentViewer = viewer.current;
    setLoadError("");
    void currentViewer.moveTo(imageId).then(
      () => {
        if (viewer.current !== currentViewer || navigation.current !== navigationId) return;
        recoveryAttempts.current = 0;
      },
      (error: unknown) => {
        const stale = viewer.current !== currentViewer || navigation.current !== navigationId;
        if (stale) return;
        if (error instanceof CancelMapillaryError) {
          console.error("Mapillary image navigation was cancelled", error);
        } else {
          console.error("Mapillary image failed to load", error);
        }
        setLoadError(LOAD_ERROR);
      },
    );
  }, [accessToken, imageId]);

  return (
    <div className="imagery">
      <div className="mapillary-host" ref={host} />
      {(isDemo || loadError) && (
        <div className="imagery-empty">
          <div className="globe">◎</div>
          <h2>Imagery preview unavailable</h2>
          <p>
            {loadError
              || "Add a public Mapillary client token and seed real image IDs to explore this round."}
          </p>
          {loadError && <button className="primary imagery-retry" onClick={retry}>Retry street view</button>}
        </div>
      )}
      <a className="mapillary-credit" href="https://www.mapillary.com/" target="_blank" rel="noreferrer">
        Mapillary
      </a>
    </div>
  );
}
