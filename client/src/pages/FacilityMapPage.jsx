import React from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";

const FacilityMapPage = () => {
  return (
    <main className="flex-1 overflow-y-auto p-6">
      <div className="bg-surface p-6 rounded-xl shadow h-[500px]">
        <MapContainer
          center={[51.505, -0.09]}
          zoom={13}
          scrollWheelZoom={true}
          className="h-full w-full rounded-lg"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Marker position={[51.505, -0.09]}>
            <Popup>Facility Location</Popup>
          </Marker>
        </MapContainer>
      </div>
    </main>
  );
};

export default FacilityMapPage;
