import React, { useRef, useState, useEffect, useMemo } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import ChartDataLabels from "chartjs-plugin-datalabels";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, ChartDataLabels);

function HourlyLambdaChart({ values, onChange }) {
  const chartRef = useRef(null);
  const [draggingIndex, setDraggingIndex] = useState(null);

  // Memoize chart data to prevent unnecessary re-renders
  const data = useMemo(() => ({
    labels: values.map((_, i) => `Hour ${i + 1}`),
    datasets: [
      {
        label: "Hourly Lambda",
        data: values,
        borderColor: "rgba(34, 197, 94, 1)",
        backgroundColor: "rgba(34, 197, 94, 0.2)",
        pointBackgroundColor: "rgba(34, 197, 94, 1)",
        pointRadius: 6,
        pointHoverRadius: 8,
        tension: 0.2,
      },
    ],
  }), [values]);

  // Memoize chart options to prevent unnecessary re-renders
  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      datalabels: {
        color: "#fff",
        anchor: "end",
        align: "top",
        offset: 4,
        font: { weight: "bold", size: 12 },
        formatter: (value) => value, // show the y-value
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        suggestedMax: Math.max(...values, 10) + 2,
        ticks: { stepSize: 1 },
      },
    },
    animation: false,
    onHover: (event, chartElements) => {
        const target = event.native?.target || event.target; // canvas element
        if (chartElements.length) {
          target.style.cursor = "pointer"; // over a point
        } else {
          target.style.cursor = "default";
              }
  }, // elsewhere
  }), [values]);

  // --- Dragging logic ---
  const handleMouseDown = (event) => {
    const chart = chartRef.current;
    if (!chart) return;

    const points = chart.getElementsAtEventForMode(
      event,
      "nearest",
      { intersect: true },
      false
    );

    if (points.length) {
      setDraggingIndex(points[0].index);
    }
  };

  const handleMouseMove = (event) => {
    if (draggingIndex === null) return;
    const chart = chartRef.current;
    if (!chart) return;

    const yScale = chart.scales.y;
    const rect = chart.canvas.getBoundingClientRect();
    const mouseY = event.clientY - rect.top;

    let newValue = yScale.getValueForPixel(mouseY);
    newValue = Math.min(yScale.max, Math.max(yScale.min, newValue));

    const updated = [...values];
    updated[draggingIndex] = Math.round(newValue);
    onChange(updated);
  };

  const handleMouseUp = () => setDraggingIndex(null);

  useEffect(() => {
    if (draggingIndex !== null) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    } else {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [draggingIndex, values]);

  return (
    <div className="h-64">
      <Line ref={chartRef} data={data} options={options} onMouseDown={handleMouseDown} />
    </div>
  );
}

export default React.memo(HourlyLambdaChart);
