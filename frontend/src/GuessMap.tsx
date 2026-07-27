import { useEffect, useRef } from "react";
import maplibregl, { GeoJSONSource, Map } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Coordinate, GuessResult } from "./types";

type Props = {
  styleUrl: string;
  value: Coordinate | null;
  result?: GuessResult | null;
  onChange?: (coordinate: Coordinate) => void;
  interactive?: boolean;
};

export function GuessMap({ styleUrl, value, result, onChange, interactive = true }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const map = new maplibregl.Map({
      container: host.current,
      style: styleUrl,
      center: [0, 15],
      zoom: 1.15,
      interactive,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
    if (interactive && onChange) {
      map.on("click", (event) =>
        onChange({ latitude: event.lngLat.lat, longitude: event.lngLat.lng }),
      );
    }
    mapRef.current = map;
    return () => map.remove();
  }, [styleUrl, interactive, onChange]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !value) return;
    markerRef.current?.remove();
    markerRef.current = new maplibregl.Marker({ color: "#ffcf54" })
      .setLngLat([value.longitude, value.latitude])
      .addTo(map);
  }, [value]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !result) return;
    const show = () => {
      new maplibregl.Marker({ color: "#36d399" })
        .setLngLat([result.actual.longitude, result.actual.latitude])
        .addTo(map);
      const data: GeoJSON.Feature = {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: [
            [result.guess.longitude, result.guess.latitude],
            [result.actual.longitude, result.actual.latitude],
          ],
        },
      };
      map.addSource("result-line", { type: "geojson", data });
      map.addLayer({
        id: "result-line",
        type: "line",
        source: "result-line",
        paint: { "line-color": "#ffcf54", "line-width": 3, "line-dasharray": [2, 2] },
      });
      const bounds = new maplibregl.LngLatBounds()
        .extend([result.guess.longitude, result.guess.latitude])
        .extend([result.actual.longitude, result.actual.latitude]);
      map.fitBounds(bounds, { padding: 60, maxZoom: 8 });
    };
    map.loaded() ? show() : map.once("load", show);
  }, [result]);

  return <div className="guess-map" ref={host} aria-label="World map" />;
}
