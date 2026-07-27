import { useEffect, useRef } from "react";
import { Viewer } from "mapillary-js";
import "mapillary-js/dist/mapillary.css";

type Props = { imageId: string; accessToken: string };

export function MapillaryView({ imageId, accessToken }: Props) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!host.current || !accessToken || imageId.startsWith("demo-")) return;
    const viewer = new Viewer({
      accessToken,
      container: host.current,
      imageId,
      component: { cover: false, sequence: true },
    });
    return () => viewer.remove();
  }, [accessToken, imageId]);

  const isDemo = imageId.startsWith("demo-") || !accessToken;
  return (
    <div className="imagery" ref={host}>
      {isDemo && (
        <div className="imagery-empty">
          <div className="globe">◎</div>
          <h2>Imagery preview unavailable</h2>
          <p>Add a public Mapillary client token and seed real image IDs to explore this round.</p>
        </div>
      )}
      <a className="mapillary-credit" href="https://www.mapillary.com/" target="_blank" rel="noreferrer">
        Mapillary
      </a>
    </div>
  );
}
