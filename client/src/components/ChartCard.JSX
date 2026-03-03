import React from "react";
import CardBase from "./CardBase";

const ChartCard = ({ title, children, className = "" }) => {
  return (
    <CardBase title={title} className={className}>
      <div className="h-56 flex items-center justify-center text-text-secondary">
        {children}
      </div>
    </CardBase>
  );
};

export default ChartCard;
