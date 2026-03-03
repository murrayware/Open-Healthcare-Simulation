import React from "react";
import CardBase from "./CardBase";

const StatCard = ({
  title,
  value,
  unit = "",
  label = "",
  className = "",
  // new props for adjusted/secondary metrics
  adjustedValue = null,
  adjustedUnit = "",
  adjustedLabel = "",
}) => {
  return (
    <CardBase title={
      <div className="flex items-center gap-2">
        <span>{title}</span>
        {label && <span className="text-sm text-text-secondary text-opacity-50">[{label}]</span>}
      </div>
    } className={className}>
      
      <div className="flex items-start justify-between mt-2">
        {/* Left: primary (default) */}
        <div>
          <div className="flex items-baseline">
            <p className="text-3xl font-bold">{value ?? "N/A"}</p>
            {unit && <span className="ml-1 text-sm text-text-secondary">{unit}</span>}
          </div>
        </div>

        {/* Right: adjusted (mirrors left layout) */}
        {adjustedValue !== null && adjustedValue !== undefined ? (
          <div className="text-right">
            <div className="flex items-baseline justify-end">
              <p className="text-3xl font-bold">{adjustedValue}</p>
              {adjustedUnit && <span className="ml-1 text-sm text-text-secondary">{adjustedUnit}</span>}
            </div>
          </div>
        ) : null}
      </div>
    </CardBase>
  );
};

export default StatCard;
