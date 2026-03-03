import React from "react";
import CardBase from "./CardBase";

const ChartCard = ({ title, children, className = "" }) => {
  return (
    <CardBase title={title} className={className}>
      <div className="flex-1 w-full h-72"> {/* taller, fills width */}
        {children}
      </div>
    </CardBase>
  );
};

export default ChartCard;
