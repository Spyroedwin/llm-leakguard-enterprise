import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import { useMemo } from "react";
import { api } from "@/lib/api";
import type { Marker } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";

type Props = { live: boolean };

export function AttackMap({ live }: Props) {
  const { data, error } = usePoll(api.markers, 2500, live);
  const markers = (data ?? []) as Marker[];

  const center = useMemo<[number, number]>(() => {
    if (markers.length) return [markers[0].lat, markers[0].lng];
    return [20.5937, 78.9629];
  }, [markers]);

  return (
    <div className="relative h-[320px] w-full overflow-hidden rounded-xl border">
      {/* Error banner (doesn't kill the map tiles) */}
      {error ? (
        <div className="absolute z-[999] left-2 top-2 rounded-md bg-destructive px-2 py-1 text-xs text-white">
          Markers API down (tiles still OK)
        </div>
      ) : null}

      <MapContainer
        center={center}
        zoom={markers.length ? 2 : 4}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />

        {markers.map((m, idx) => (
          <CircleMarker
            key={`${m.lat}-${m.lng}-${idx}`}
            center={[m.lat, m.lng]}
            radius={m.tor ? 8 : 6}
            pathOptions={{ opacity: 0.9 }}
          >
            <Tooltip opacity={1}>
              <div className="text-xs">
                <div className="font-medium">{m.label ?? "unknown"}</div>
                {m.threat ? <div>threat: {m.threat}</div> : null}
                {typeof m.risk === "number" ? (
                  <div>risk: {m.risk.toFixed(2)}</div>
                ) : null}
                {m.tor ? <div className="font-semibold">TOR exit</div> : null}
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
