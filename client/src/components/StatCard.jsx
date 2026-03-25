import React from "react";
import { Box, Typography } from "@mui/material";
import CardBase from "./CardBase";
import { useAppTheme } from "../theme/useTheme";

const StatCard = ({
  title,
  defaultValue,
  adjustedValue = null,
  unit = "",
  label = "",
  className = "",
  showAdjusted = false,
  showNoChangePillWhenDefaultOnly = false,
  isWholeNumber = false, // New prop to format comparison as whole number
  changeType = "lower-is-better", // "lower-is-better", "higher-is-better", or "neutral"
}) => {
  const appTheme = useAppTheme();
  const hasAdjusted = adjustedValue !== null && adjustedValue !== undefined;
  
  const formatValue = (value) => {
    if (value === null || value === undefined) return "N/A";
    return value;
  };
  
  // Calculate comparison when adjusted and default both exist
  let comparison = null;
  if (hasAdjusted && defaultValue !== null && defaultValue !== undefined) {
    const numericDefault = typeof defaultValue === 'string' ? parseFloat(defaultValue) : defaultValue;
    const numericAdjusted = typeof adjustedValue === 'string' ? parseFloat(adjustedValue) : adjustedValue;
    
    if (!isNaN(numericDefault) && !isNaN(numericAdjusted)) {
      const change = numericAdjusted - numericDefault;
      const absChange = Math.abs(change);
      
      // Only show comparison if change is significant (>= 0.1)
      if (absChange >= 0.1) {
        let isImprovement;
        if (changeType === "neutral") {
          isImprovement = null; // Neutral change
        } else if (changeType === "higher-is-better") {
          isImprovement = change > 0; // Higher values are better
        } else {
          isImprovement = change < 0; // Lower values are better (default)
        }
        
        comparison = {
          change: isWholeNumber ? Math.round(absChange) : absChange,
          isImprovement,
          symbol: change < 0 ? '-' : '+',
          isNeutral: changeType === "neutral"
        };
      }
    }
  }
  
  return (
    <CardBase title={
      <div className="flex items-center gap-2">
        <span className="text-sm">{title}</span>
        {label && <span className="text-xs text-text-secondary text-opacity-35">[{label}]</span>}
      </div>
    } className={`w-full ${className}`}>
      
      {hasAdjusted ? (
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mt: 2, gap: 1, minHeight: 86 }}>
          <Box sx={{ flex: 1, opacity: 0.35 }}>
            <Typography sx={{ fontSize: '0.62rem', color: 'text.secondary', lineHeight: 1, mb: 0.35, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Default
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'baseline' }}>
              <Typography sx={{ fontSize: '1.9rem', fontWeight: 700, lineHeight: 1.1 }}>
                {formatValue(defaultValue)}
              </Typography>
              {unit && <Typography sx={{ ml: 0.5, fontSize: '0.9rem', color: 'text.secondary' }}>{unit}</Typography>}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', px: 0.75, alignSelf: 'flex-start', pt: 1.25 }}>
            <Typography sx={{ color: appTheme.colors.text.secondary, fontSize: '2.1rem', fontWeight: 700, lineHeight: 1, opacity: 0.35 }}>
              /
            </Typography>
          </Box>

          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <Typography sx={{ fontSize: '0.62rem', color: 'text.secondary', lineHeight: 1, mb: 0.35, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Tuned
            </Typography>
            <Box sx={{ display: 'inline-flex', alignItems: 'baseline', justifyContent: 'flex-end' }}>
              <Typography sx={{ fontSize: '1.9rem', fontWeight: 700, lineHeight: 1.1 }}>
                {formatValue(adjustedValue)}
              </Typography>
              {unit && <Typography sx={{ ml: 0.5, fontSize: '0.9rem', color: 'text.secondary' }}>{unit}</Typography>}
            </Box>

            {comparison ? (
              <Box sx={{ 
                display: 'inline-flex',
                alignItems: 'center',
                px: 1,
                py: 0.25,
                mt: 0.5,
                borderRadius: '12px',
                backgroundColor: comparison.isNeutral 
                  ? appTheme.colors.background.surface
                  : comparison.isImprovement 
                    ? `${appTheme.colors.success.main}20` 
                    : `${appTheme.colors.error.main}20`,
              }}>
                <Typography sx={{ 
                  fontSize: '0.7rem', 
                  color: comparison.isNeutral 
                    ? 'text.secondary'
                    : comparison.isImprovement 
                      ? 'success.main' 
                      : 'error.main',
                  lineHeight: 1.4,
                  fontWeight: 600
                }}>
                  {comparison.symbol} {isWholeNumber ? comparison.change : comparison.change.toFixed(1)} {unit}
                </Typography>
              </Box>
            ) : (
              <Box sx={{ 
                display: 'inline-flex',
                alignItems: 'center',
                px: 1,
                py: 0.25,
                mt: 0.5,
                borderRadius: '12px',
                backgroundColor: appTheme.colors.background.surface,
              }}>
                <Typography sx={{ 
                  fontSize: '0.7rem', 
                  color: 'text.disabled',
                  lineHeight: 1.4,
                  fontWeight: 500
                }}>
                  — no change
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center', mt: 2, minHeight: 86 }}>
          <Box sx={{ textAlign: 'center' }}>
            <Typography sx={{ fontSize: '0.62rem', color: 'text.secondary', lineHeight: 1, mb: 0.35, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Default
            </Typography>
            <div className="flex items-baseline justify-center">
              <p className="text-3xl font-bold">{formatValue(defaultValue)}</p>
              {unit && <span className="ml-1 text-sm text-text-secondary">{unit}</span>}
            </div>
            {showNoChangePillWhenDefaultOnly && (
              <Box sx={{ 
                display: 'inline-flex',
                alignItems: 'center',
                px: 1,
                py: 0.25,
                mt: 0.5,
                borderRadius: '12px',
                backgroundColor: appTheme.colors.background.surface,
              }}>
                <Typography sx={{ 
                  fontSize: '0.7rem', 
                  color: 'text.disabled',
                  lineHeight: 1.4,
                  fontWeight: 500
                }}>
                  — no change
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      )}
    </CardBase>
  );
};

export default StatCard;
