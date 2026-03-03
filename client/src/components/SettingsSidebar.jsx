import React, { useMemo, useState, useEffect } from "react";
import {
  Drawer,
  IconButton,
  Box,
  Button,
  useTheme,
  useMediaQuery,
  Backdrop,
  CircularProgress,
  Typography,
  Badge,
} from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import SettingsIcon from "@mui/icons-material/Settings";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import PersonIcon from "@mui/icons-material/Person";
import DirectionsCarIcon from "@mui/icons-material/DirectionsCar";
import HotelIcon from "@mui/icons-material/Hotel";
import DomainIcon from "@mui/icons-material/Domain";
import FastfoodIcon from "@mui/icons-material/Fastfood";
import { useAppTheme } from "../theme/useTheme";

const COLLAPSED_WIDTH = 60;

// Lazy load the settings content
const SettingsDrawerContent = React.lazy(() => 
  import("../pages/settings/SettingsDrawerContent")
);

const SettingsSidebar = ({ 
  simulation,
  onSettingsChange 
}) => {
  const theme = useTheme();
  const appTheme = useAppTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));
  const [open, setOpen] = useState(false);
  const [shouldRenderContent, setShouldRenderContent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const onToggle = () => setOpen(!open);
  const onClose = () => setOpen(false);

  // Only render content when sidebar is open, with a small delay to prevent premature loading
  useEffect(() => {
    if (open) {
      setIsLoading(true);
      setShouldRenderContent(false);
      // Delay content rendering slightly to allow sidebar animation to start
      const timer = setTimeout(() => {
        setShouldRenderContent(true);
        setIsLoading(false);
      }, 150);
      return () => {
        clearTimeout(timer);
        setIsLoading(false);
      };
    } else {
      // Immediately stop rendering content when closed to improve performance
      setShouldRenderContent(false);
      setIsLoading(false);
    }
  }, [open]);

  // Memoize expanded width calculation to avoid recalculation on every render
  const expandedWidth = useMemo(() => {
    return typeof window !== 'undefined' ? Math.floor(window.innerWidth * 0.75) : 600;
  }, []);

  // Calculate settings summary for collapsed view
  const settingsSummary = useMemo(() => {
    if (!simulation?.settings) return null;
    
    const settings = simulation.settings;
    const summary = {
      physicians: settings.doctors?.length || 0,
      edAreas: Object.keys(settings.areas || {}).length + (settings.fasttrack?.enabled ? 1 : 0),
      ems: settings.ems?.enabled ? 1 : 0,
      inpatientUnits: Object.keys(settings.inpatient?.units || {}).length,
      capabilities: Object.keys(settings.capabilities || {}).length,
    };
    
    return summary;
  }, [simulation?.settings]);

  return (
    <>
      {/* Mobile Settings Drawer - Full overlay */}
      <Drawer
        variant="temporary"
        anchor="left"
        open={open && isMobile}
        onClose={onClose}
        ModalProps={{
          keepMounted: true,
        }}
        sx={{
          display: { xs: 'block', lg: 'none' },
          '& .MuiDrawer-paper': {
            width: '100%',
            maxWidth: expandedWidth,
            backgroundColor: appTheme.colors.background.sidebar,
            borderRight: `1px solid ${appTheme.colors.border.default}`,
          },
        }}
        >
          {(isLoading || shouldRenderContent) && (
            <>
              {isLoading && (
                <div className="flex flex-col items-center justify-center h-full space-y-3">
                  <CircularProgress size={40} sx={{ color: appTheme.colors.primary.main }} />
                  <div className="text-gray-400 text-sm">Loading settings...</div>
                </div>
              )}
              {shouldRenderContent && (
                <React.Suspense fallback={
                  <div className="flex flex-col items-center justify-center h-full space-y-3">
                    <CircularProgress size={40} sx={{ color: appTheme.colors.primary.main }} />
                    <div className="text-gray-400 text-sm">Loading settings...</div>
                  </div>
                }>
                  <SettingsDrawerContent 
                    onClose={onClose}
                    simulation={simulation}
                    onSettingsChange={onSettingsChange}
                  />
                </React.Suspense>
              )}
            </>
          )}
        </Drawer>      {/* Desktop - Always visible collapsed/expanded sidebar */}
      {!isMobile && (
        <>
          {/* Backdrop when expanded - positioned relative to the parent container */}
          <Backdrop
            open={open}
            onClick={onClose}
            sx={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              height: '100%',
              zIndex: 29,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: open ? 'block' : 'none',
            }}
          />

          <div
            className="absolute left-0 top-0 h-full border-r transition-all duration-300 ease-in-out z-30 overflow-hidden"
            style={{ 
              width: open ? expandedWidth : COLLAPSED_WIDTH,
              backgroundColor: appTheme.colors.background.sidebar,
              borderRightColor: appTheme.colors.border.secondary,
            }}
          >
          {/* Expanded Content */}
          {open && (
            <div className="h-full overflow-y-auto">
              {isLoading && (
                <div className="flex flex-col items-center justify-center h-full space-y-3">
                  <CircularProgress size={40} sx={{ color: appTheme.colors.primary.main }} />
                  <div className="text-gray-400 text-sm">Loading settings...</div>
                </div>
              )}
              {shouldRenderContent && (
                <React.Suspense fallback={
                  <div className="flex flex-col items-center justify-center h-full space-y-3">
                    <CircularProgress size={40} sx={{ color: appTheme.colors.primary.main }} />
                    <div className="text-gray-400 text-sm">Loading settings...</div>
                  </div>
                }>
                  <SettingsDrawerContent 
                    onClose={onClose}
                    simulation={simulation}
                    onSettingsChange={onSettingsChange}
                  />
                </React.Suspense>
              )}
            </div>
          )}

          {/* Collapsed Content */}
          {!open && (
            <div className="h-full flex flex-col items-center py-4 space-y-4">
              <Button
                onClick={onToggle}
                variant='contained'
                sx={{
                  borderTopRightRadius: 0,
                  borderBottomRightRadius: 0,
                  height: 40,
                }}
              >
                <SettingsIcon 
                />
              </Button>
              
              {/* Settings Summary */}
              {settingsSummary && (
                <div className="flex flex-col items-center space-y-3 mt-4">
                  {/* Physicians */}
                  <div className="flex flex-col items-center">
                    <Badge
                      badgeContent={settingsSummary.physicians}
                      color="primary"
                      sx={{
                        '& .MuiBadge-badge': {
                          right: -3,
                          top: 3,
                          fontSize: '0.7rem',
                          minWidth: 16,
                          height: 16,
                        },
                      }}
                    >
                      <PersonIcon sx={{ color: appTheme.colors.text.secondary, fontSize: 20 }} />
                    </Badge>
                    <Typography variant="caption" sx={{ color: appTheme.colors.text.secondary, fontSize: '0.6rem', mt: 0.5 }}>
                      Docs
                    </Typography>
                  </div>

                  {/* ED Areas */}
                  <div className="flex flex-col items-center">
                    <Badge
                      badgeContent={settingsSummary.edAreas}
                      color="primary"
                      sx={{
                        '& .MuiBadge-badge': {
                          right: -3,
                          top: 3,
                          fontSize: '0.7rem',
                          minWidth: 16,
                          height: 16,
                        },
                      }}
                    >
                      <LocalHospitalIcon sx={{ color: appTheme.colors.text.secondary, fontSize: 20 }} />
                    </Badge>
                    <Typography variant="caption" sx={{ color: appTheme.colors.text.secondary, fontSize: '0.6rem', mt: 0.5 }}>
                      Areas
                    </Typography>
                  </div>

                  {/* EMS */}
                  {settingsSummary.ems > 0 && (
                    <div className="flex flex-col items-center">
                      <DirectionsCarIcon sx={{ color: appTheme.colors.success.main, fontSize: 20 }} />
                      <Typography variant="caption" sx={{ color: appTheme.colors.text.secondary, fontSize: '0.6rem', mt: 0.5 }}>
                        EMS
                      </Typography>
                    </div>
                  )}

                  {/* Inpatient Units */}
                  <div className="flex flex-col items-center">
                    <Badge
                      badgeContent={settingsSummary.inpatientUnits}
                      color="primary"
                      sx={{
                        '& .MuiBadge-badge': {
                          right: -3,
                          top: 3,
                          fontSize: '0.7rem',
                          minWidth: 16,
                          height: 16,
                        },
                      }}
                    >
                      <HotelIcon sx={{ color: appTheme.colors.text.secondary, fontSize: 20 }} />
                    </Badge>
                    <Typography variant="caption" sx={{ color: appTheme.colors.text.secondary, fontSize: '0.6rem', mt: 0.5 }}>
                      Units
                    </Typography>
                  </div>

                  {/* Capabilities */}
                  <div className="flex flex-col items-center">
                    <Badge
                      badgeContent={settingsSummary.capabilities}
                      color="primary"
                      sx={{
                        '& .MuiBadge-badge': {
                          right: -3,
                          top: 3,
                          fontSize: '0.7rem',
                          minWidth: 16,
                          height: 16,
                        },
                      }}
                    >
                      <DomainIcon sx={{ color: appTheme.colors.text.secondary, fontSize: 20 }} />
                    </Badge>
                    <Typography variant="caption" sx={{ color: appTheme.colors.text.secondary, fontSize: '0.6rem', mt: 0.5 }}>
                      Caps
                    </Typography>
                  </div>
                </div>
              )}
              

            </div>
          )}
          </div>
        </>
      )}
    </>
  );
};

export default React.memo(SettingsSidebar);