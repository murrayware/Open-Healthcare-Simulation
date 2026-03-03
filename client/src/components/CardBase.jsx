import React from "react";

const CardBase = ({ title, className = "", children }) => {
  return (
    <div className={`bg-surface p-6 rounded-xl shadow ${className}`}>
      <h2 className="text-md uppercase text-text-secondary font-bold ">{title}</h2>
      {children}
    </div>
  );
};

export default CardBase;
