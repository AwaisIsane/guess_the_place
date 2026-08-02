import { useEffect, useRef } from "react";
import {
  AttributionControl,
  LngLatBounds,
  Map,
  Marker,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Coordinate, GuessResult } from "./types";

setWorkerUrl(maplibreWorkerUrl);

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
  const markerRef = useRef<Marker | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const map = new Map({
      container: host.current,
      style: styleUrl,
      center: [0, 15],
      zoom: 1.15,
      interactive,
      attributionControl: false,
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new AttributionControl({ compact: true }), "bottom-left");
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
    markerRef.current = new Marker({ color: "#ffcf54" })
      .setLngLat([value.longitude, value.latitude])
      .addTo(map);
  }, [value]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !result) return;

    const actualMarker = new Marker({ color: "#36d399" })
      .setLngLat([result.actual.longitude, result.actual.latitude])
      .addTo(map);
    const bounds = new LngLatBounds()
      .extend([result.guess.longitude, result.guess.latitude])
      .extend([result.actual.longitude, result.actual.latitude]);
    map.fitBounds(bounds, { padding: 60, maxZoom: 8 });

    const show = () => {
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
      if (!map.getSource("result-line")) {
        map.addSource("result-line", { type: "geojson", data });
        map.addLayer({
          id: "result-line",
          type: "line",
          source: "result-line",
          paint: { "line-color": "#ffcf54", "line-width": 3, "line-dasharray": [2, 2] },
        });
      }
    };
    if (map.isStyleLoaded()) show();
    else map.once("style.load", show);

    return () => {
      actualMarker.remove();
      map.off("style.load", show);
    };
  }, [result]);

  return <div className="guess-map" ref={host} aria-label="World map" />;
}
