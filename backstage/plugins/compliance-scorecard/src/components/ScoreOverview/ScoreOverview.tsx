/**
 * ScoreOverview — Score gauge + classification badge.
 *
 * Displays overall compliance score (0-100) with color-coded classification
 * and severity counters (Critical / High / Medium / Low).
 */

import React from 'react';
import { makeStyles } from '@material-ui/core/styles';
import { Box, Typography, Chip, CircularProgress, Tooltip } from '@material-ui/core';
import type { ScoresResponse } from '../../api/ComplianceApi';

const CLASSIFICATION_COLORS: Record<string, string> = {
  excellent: '#22c55e',  // green
  good: '#3b82f6',       // blue
  fair: '#f59e0b',       // amber
  poor: '#ef4444',       // red
};

const CLASSIFICATION_LABELS: Record<string, string> = {
  excellent: '🟢 Excellent',
  good: '🔵 Good',
  fair: '🟡 Fair',
  poor: '🔴 Poor',
};

const useStyles = makeStyles(theme => ({
  root: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: theme.spacing(3),
    gap: theme.spacing(1.5),
  },
  gaugeWrap: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  gaugeBackground: {
    color: theme.palette.action.disabledBackground,
  },
  gaugeForeground: {
    position: 'absolute',
    transition: 'color 0.3s ease',
  },
  scoreText: {
    position: 'absolute',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  scoreValue: {
    fontWeight: 700,
    lineHeight: 1,
  },
  scoreMax: {
    fontSize: '0.7rem',
    color: theme.palette.text.secondary,
  },
  badge: {
    fontWeight: 600,
    fontSize: '0.85rem',
  },
  severities: {
    display: 'flex',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: theme.spacing(1),
  },
  sev: {
    fontSize: '0.75rem',
    fontWeight: 500,
  },
}));

interface Props {
  scores: ScoresResponse;
}

export function ScoreOverview({ scores }: Props) {
  const classes = useStyles();
  const color = CLASSIFICATION_COLORS[scores.classification] ?? '#94a3b8';
  const label = CLASSIFICATION_LABELS[scores.classification] ?? scores.classification;
  const pct = Math.round(scores.overall_score);

  return (
    <Box className={classes.root}>
      <div className={classes.gaugeWrap}>
        <CircularProgress
          className={classes.gaugeBackground}
          variant="determinate"
          value={100}
          size={140}
          thickness={5}
        />
        <CircularProgress
          className={classes.gaugeForeground}
          style={{ color }}
          variant="determinate"
          value={pct}
          size={140}
          thickness={5}
        />
        <div className={classes.scoreText}>
          <Typography variant="h3" className={classes.scoreValue} style={{ color }}>
            {pct}
          </Typography>
          <span className={classes.scoreMax}>/ 100</span>
        </div>
      </div>

      <Chip
        label={label}
        className={classes.badge}
        style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}` }}
      />

      <Box className={classes.severities}>
        <Tooltip title="Critical findings">
          <Chip
            label={`🔴 ${scores.critical_violations} Critical`}
            size="small"
            className={classes.sev}
            style={{ backgroundColor: '#fef2f2', color: '#ef4444' }}
          />
        </Tooltip>
        <Tooltip title="High findings">
          <Chip
            label={`🟠 ${scores.high_violations} High`}
            size="small"
            className={classes.sev}
            style={{ backgroundColor: '#fff7ed', color: '#f97316' }}
          />
        </Tooltip>
        <Tooltip title="Total failed checks">
          <Chip
            label={`❌ ${scores.total_failed} Failed`}
            size="small"
            className={classes.sev}
            style={{ backgroundColor: '#fafafa', color: '#64748b' }}
          />
        </Tooltip>
        <Tooltip title="Total passed checks">
          <Chip
            label={`✅ ${scores.total_passed} Passed`}
            size="small"
            className={classes.sev}
            style={{ backgroundColor: '#f0fdf4', color: '#22c55e' }}
          />
        </Tooltip>
      </Box>
    </Box>
  );
}
