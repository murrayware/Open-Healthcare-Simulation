// Performance monitoring hook for debugging React performance issues
import { useEffect, useRef, useMemo } from 'react';

export const usePerformanceMonitor = (componentName, dependencies = []) => {
  const renderCount = useRef(0);
  const lastRender = useRef(Date.now());

  useEffect(() => {
    renderCount.current += 1;
    const now = Date.now();
    const timeSinceLastRender = now - lastRender.current;
    
    // Log renders that happen too frequently (less than 16ms apart = >60fps)
    if (timeSinceLastRender < 16 && renderCount.current > 1) {
      console.warn(`🚨 ${componentName} rendering too frequently! 
        Render #${renderCount.current} after ${timeSinceLastRender}ms
        Dependencies:`, dependencies);
    }
    
    // Log every 10th render for monitoring
    if (renderCount.current % 10 === 0) {
      console.log(`📊 ${componentName} rendered ${renderCount.current} times`);
    }
    
    lastRender.current = now;
  });

  // Return render count for debugging
  return renderCount.current;
};

// Hook to monitor expensive operations
export const useExpensiveOperation = (operationName, operation, dependencies) => {
  return useMemo(() => {
    const start = performance.now();
    const result = operation();
    const end = performance.now();
    
    if (end - start > 10) { // Log operations taking more than 10ms
      console.warn(`🐌 Slow operation "${operationName}": ${(end - start).toFixed(2)}ms`);
    }
    
    return result;
  }, dependencies);
};