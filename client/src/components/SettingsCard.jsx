import React from "react";
import { Card, CardContent, Typography, Box } from "@mui/material";

const SettingsCard = ({ title, children, footer, className = "" }) => {
  return (
    <Card
    elevation={0}
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
      className={className}
    >
      {/* Title */}
      {title && (
        <Box sx={{ p: 2, pb: 0 }}>
          <Typography
            variant="h6"
            component="h2"
            sx={{
              textTransform: "uppercase",
              fontWeight: "bold",
              color: "text.secondary",
              fontSize: "0.875rem",
            }}
          >
            {title}
          </Typography>
        </Box>
      )}

      {/* Content */}
      <CardContent
        sx={{
          flex: 1,
          overflow: "auto",
          "&:last-child": {
            paddingBottom: footer ? 1 : 2,
          },
        }}
      >
        {children}
      </CardContent>

      {/* Optional footer (buttons, actions) */}
      {footer && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            gap: 2,
            p: 2,
            pt: 0,
          }}
        >
          {footer}
        </Box>
      )}
    </Card>
  );
};

export default SettingsCard;
