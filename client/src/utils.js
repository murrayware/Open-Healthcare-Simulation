export function generateSineWave(length, min, max, cycles = 1, phase = 0) {
  const amplitude = (max - min) / 2;
  const midpoint = (max + min) / 2;

  return Array.from({ length }, (_, i) => {
    const angle = ((i / length) * cycles * 2 * Math.PI) + phase;
    return Math.round(midpoint + amplitude * Math.sin(angle));
  });
}


export function generateStepDecay(length, start, end, steps) {
  const values = [];
  const stepSize = Math.floor(length / steps);
  let current = start;
  for (let i = 0; i < steps; i++) {
    for (let j = 0; j < stepSize; j++) values.push(current);
    current = Math.max(end, current - 1);
  }
  return values.slice(0, length);
}



export const normalizeService = (s) => (s || "").trim();

export const isDuplicateService = (units, name, editingIndex) =>
  units.some(
    (u, i) =>
      normalizeService(u.service).toLowerCase() ===
        normalizeService(name).toLowerCase() && i !== editingIndex
  );

export const ensureLambda = (lambdaMap, service, hours) => {
  if (lambdaMap[service]) return lambdaMap;
  return {
    ...lambdaMap,
    [service]: generateSineWave(hours, 0, 5, 1, -Math.PI / 2),
  };
};



// Recursively walk an object and round floats

export const roundFloats = (obj) => {
  if (Array.isArray(obj)) {
    return obj.map(roundFloats);
  } else if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [k, roundFloats(v)])
    );
  } else if (typeof obj === "number") {
    // If it's an integer, return as-is
    if (Number.isInteger(obj)) return obj;
    // If it's a float, round to 1 decimal
    return parseFloat(obj.toFixed(1));
  }
  return obj;
};
