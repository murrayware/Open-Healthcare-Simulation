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
  Tooltip,
} from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CloseIcon from "@mui/icons-material/Close";
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
  onSettingsChange,
  showTooltip = false,
  onTooltipDismiss
}) => {
  const theme = useTheme();
  const appTheme = useAppTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));
  const [open, setOpen] = useState(false);
  const [shouldRenderContent, setShouldRenderContent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [quickAction, setQuickAction] = useState(null);

  const onToggle = () => {
    setOpen(!open);
    // Dismiss tooltip when opening settings drawer
    if (!open && onTooltipDismiss) {
      onTooltipDismiss();
    }
  };
  const onClose = () => {
    setOpen(false);
    setQuickAction(null);
  };

  const handleQuickAction = (target) => {
    setOpen(true);
    setQuickAction({ target, token: Date.now() });
    if (onTooltipDismiss) {
      onTooltipDismiss();
    }
  };

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
                    quickAction={quickAction}
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
                    quickAction={quickAction}
                  />
                </React.Suspense>
              )}
            </div>
          )}

          {/* Collapsed Content */}
          {!open && (
            <div className="h-full flex flex-col items-center py-4 space-y-4">
              <Tooltip
                open={showTooltip}
                title={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span>Click here to configure hospital settings before running</span>
                    {onTooltipDismiss && (
                      <IconButton
                        size="small"
                        onClick={onTooltipDismiss}
                        sx={{ 
                          color: 'inherit', 
                          padding: 0,
                          minWidth: 'auto',
                          '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' }
                        }}
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    )}
                  </Box>
                }
                arrow
                placement="right"
                componentsProps={{
                  tooltip: {
                    sx: {
                      bgcolor: 'primary.main',
                      '& .MuiTooltip-arrow': {
                        color: 'primary.main',
                      },
                      fontSize: '0.875rem',
                      padding: '8px 12px'
                    }
                  }
                }}
              >
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
              </Tooltip>
              
              {/* Settings Summary */}
              {settingsSummary && (
                <div className="flex flex-col items-center space-y-3 mt-4">
                  {/* Physicians */}
                  <Box
                    role="button"
                    tabIndex={0}
                    onClick={() => handleQuickAction("add-physician")}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleQuickAction("add-physician");
                      }
                    }}
                    sx={{
                      width: 52,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 0.5,
                      cursor: 'pointer',
                      borderRadius: 2,
                      p: 0.5,
                      transition: 'all 180ms ease',
                      '&:focus-visible': {
                        outline: `2px solid ${appTheme.colors.primary.main}`,
                        outlineOffset: 2,
                      },
                      '& .quick-icon-wrap': {
                        width: 36,
                        height: 36,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        position: 'relative',
                        transition: 'all 180ms ease',
                      },
                      '& .quick-badge': {
                        transition: 'all 140ms ease',
                      },
                      '& .quick-icon': {
                        color: appTheme.colors.text.secondary,
                        fontSize: 20,
                        transition: 'all 140ms ease',
                      },
                      '& .quick-label': {
                        color: appTheme.colors.text.secondary,
                        fontSize: '0.6rem',
                        transition: 'all 140ms ease',
                      },
                      '& .quick-plus': {
                        position: 'absolute',
                        color: '#ffffff',
                        fontWeight: 700,
                        fontSize: '1rem',
                        opacity: 0,
                        transform: 'scale(0.7)',
                        transition: 'all 140ms ease',
                        pointerEvents: 'none',
                      },
                      '&:hover .quick-icon-wrap, &:focus-visible .quick-icon-wrap': {
                        borderRadius: 2,
                        backgroundColor: appTheme.colors.primary.main,
                      },
                      '&:hover .quick-badge, &:focus-visible .quick-badge': {
                        opacity: 0,
                        transform: 'scale(0.85)',
                      },
                      '&:hover .quick-plus, &:focus-visible .quick-plus': {
                        opacity: 1,
                        transform: 'scale(1)',
                      },
                    }}
                  >
                    <Box className="quick-icon-wrap">
                      <Badge
                        className="quick-badge"
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
                        <PersonIcon className="quick-icon" />
                      </Badge>
                      <Typography component="span" className="quick-plus">+</Typography>
                    </Box>
                    <Typography variant="caption" className="quick-label">
                      ED Docs
                    </Typography>
                  </Box>

                  {/* ED Areas */}
                  <Box
                    role="button"
                    tabIndex={0}
                    onClick={() => handleQuickAction("add-ed-area")}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleQuickAction("add-ed-area");
                      }
                    }}
                    sx={{
                      width: 52,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 0.5,
                      cursor: 'pointer',
                      borderRadius: 2,
                      p: 0.5,
                      transition: 'all 180ms ease',
                      '&:focus-visible': {
                        outline: `2px solid ${appTheme.colors.primary.main}`,
                        outlineOffset: 2,
                      },
                      '& .quick-icon-wrap': {
                        width: 36,
                        height: 36,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        position: 'relative',
                        transition: 'all 180ms ease',
                      },
                      '& .quick-badge': {
                        transition: 'all 140ms ease',
                      },
                      '& .quick-icon': {
                        color: appTheme.colors.text.secondary,
                        fontSize: 20,
                        transition: 'all 140ms ease',
                      },
                      '& .quick-label': {
                        color: appTheme.colors.text.secondary,
                        fontSize: '0.6rem',
                        transition: 'all 140ms ease',
                      },
                      '& .quick-plus': {
                        position: 'absolute',
                        color: '#ffffff',
                        fontWeight: 700,
                        fontSize: '1rem',
                        opacity: 0,
                        transform: 'scale(0.7)',
                        transition: 'all 140ms ease',
                        pointerEvents: 'none',
                      },
                      '&:hover .quick-icon-wrap, &:focus-visible .quick-icon-wrap': {
                        borderRadius: 2,
                        backgroundColor: appTheme.colors.primary.main,
                      },
                      '&:hover .quick-badge, &:focus-visible .quick-badge': {
                        opacity: 0,
                        transform: 'scale(0.85)',
                      },
                      '&:hover .quick-plus, &:focus-visible .quick-plus': {
                        opacity: 1,
                        transform: 'scale(1)',
                      },
                    }}
                  >
                    <Box className="quick-icon-wrap">
                      <Badge
                        className="quick-badge"
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
                        <LocalHospitalIcon className="quick-icon" />
                      </Badge>
                      <Typography component="span" className="quick-plus">+</Typography>
                    </Box>
                    <Typography variant="caption" className="quick-label">
                     ED Areas
                    </Typography>
                  </Box>

                  {/* EMS
                  {settingsSummary.ems > 0 && (
                    <div className="flex flex-col items-center">
                      <DirectionsCarIcon sx={{ color: appTheme.colors.success.main, fontSize: 20 }} />
                      <Typography variant="caption" sx={{ color: appTheme.colors.text.secondary, fontSize: '0.6rem', mt: 0.5 }}>
                        EMS
                      </Typography>
                    </div>
                  )} */}

                  {/* Inpatient Units */}
                  <Box
                    role="button"
                    tabIndex={0}
                    onClick={() => handleQuickAction("add-inpatient-unit")}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleQuickAction("add-inpatient-unit");
                      }
                    }}
                    sx={{
                      width: 52,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 0.5,
                      cursor: 'pointer',
                      borderRadius: 2,
                      p: 0.5,
                      transition: 'all 180ms ease',
                      '&:focus-visible': {
                        outline: `2px solid ${appTheme.colors.primary.main}`,
                        outlineOffset: 2,
                      },
                      '& .quick-icon-wrap': {
                        width: 36,
                        height: 36,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        position: 'relative',
                        transition: 'all 180ms ease',
                      },
                      '& .quick-badge': {
                        transition: 'all 140ms ease',
                      },
                      '& .quick-icon': {
                        color: appTheme.colors.text.secondary,
                        fontSize: 20,
                        transition: 'all 140ms ease',
                      },
                      '& .quick-label': {
                        color: appTheme.colors.text.secondary,
                        fontSize: '0.6rem',
                        transition: 'all 140ms ease',
                      },
                      '& .quick-plus': {
                        position: 'absolute',
                        color: '#ffffff',
                        fontWeight: 700,
                        fontSize: '1rem',
                        opacity: 0,
                        transform: 'scale(0.7)',
                        transition: 'all 140ms ease',
                        pointerEvents: 'none',
                      },
                      '&:hover .quick-icon-wrap, &:focus-visible .quick-icon-wrap': {
                        borderRadius: 2,
                        backgroundColor: appTheme.colors.primary.main,
                      },
                      '&:hover .quick-badge, &:focus-visible .quick-badge': {
                        opacity: 0,
                        transform: 'scale(0.85)',
                      },
                      '&:hover .quick-plus, &:focus-visible .quick-plus': {
                        opacity: 1,
                        transform: 'scale(1)',
                      },
                    }}
                  >
                    <Box className="quick-icon-wrap">
                      <Badge
                        className="quick-badge"
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
                        <HotelIcon className="quick-icon" />
                      </Badge>
                      <Typography component="span" className="quick-plus">+</Typography>
                    </Box>
                    <Typography variant="caption" className="quick-label">
                      IP Units
                    </Typography>
                  </Box>

                  {/* Capabilities
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
                  </div> */}
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