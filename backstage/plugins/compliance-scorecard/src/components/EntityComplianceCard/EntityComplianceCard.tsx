/**
 * EntityComplianceCard — Compact compliance score card for entity pages.
 *
 * Embedded in Backstage Catalog service entity pages.
 * Shows overall score, classification, and severity breakdown.
 */

import React from 'react';
import { makeStyles } from '@material-ui/core/styles';
import {
  Box,
  Typography,
  CircularProgress,
  Button,
  Chip,
  Card,
  CardContent,
  CardActions,
} from '@material-ui/core';
import SecurityIcon from '@material-ui/icons/Security';
import { useScores } from '../../hooks/useScores';

const CLASSIFICATION_CONFIG: Record<string, { label: string; color: string; emoji: string }> = {
  excellent: { label: 'Excellent', color: '#22c55e', emoji: '🟢' },
  good:      { label: 'Good',      color: '#3b82f6', emoji: '🔵' },
  fair:      { label: 'Fair',      color: '#f59e0b', emoji: '🟡' },
  poor:      { label: 'Poor',      color: '#ef4444', emoji: '🔴' },
};

const useStyles = makeStyles(theme => ({
  card: {
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    border: '1px solid #334155',
    borderRadius: 12,
    height: '100%',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    marginBottom: theme.spacing(2),
    color: '#94a3b8',
  },
  headerIcon: {
    color: '#6366f1',
    fontSize: 20,
  },
  scoreRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing(1.5),
    marginBottom: theme.spacing(2),
  },
  scoreValue: {
    fontWeight: 700,
    lineHeight: 1,
    color: '#f1f5f9',
  },
  badge: {
    fontWeight: 600,
    fontSize: '0.82rem',
  },
  severityRow: {
    display: 'flex',
    gap: theme.spacing(0.5),
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginBottom: theme.spacing(1),
  },
  sevChip: {
    fontSize: '0.72rem',
    height: 22,
  },
  viewBtn: {
    color: '#6366f1',
    fontSize: '0.8rem',
  },
}));

export function EntityComplianceCard() {
  const classes = useStyles();
  const { scores, loading, error, refresh } = useScores();

  if (loading) {
    return (
      <Card className={classes.card}>
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={120}>
            <CircularProgress size={28} style={{ color: '#6366f1' }} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error || !scores) {
    return (
      <Card className={classes.card}>
        <CardContent>
          <Typography style={{ color: '#f87171', fontSize: '0.82rem' }}>
            ⚠️ Could not load compliance data
          </Typography>
        </CardContent>
        <CardActions>
          <Button size="small" onClick={refresh} className={classes.viewBtn}>Retry</Button>
        </CardActions>
      </Card>
    );
  }

  const cls = CLASSIFICATION_CONFIG[scores.classification] ?? CLASSIFICATION_CONFIG.fair;

  return (
    <Card className={classes.card}>
      <CardContent>
        <Box className={classes.header}>
          <SecurityIcon className={classes.headerIcon} />
          <Typography variant="subtitle2" style={{ color: '#94a3b8', fontWeight: 600 }}>
            📋 Compliance Score
          </Typography>
        </Box>

        <Box className={classes.scoreRow}>
          <Typography variant="h3" className={classes.scoreValue} style={{ color: cls.color }}>
            {Math.round(scores.overall_score)}
          </Typography>
          <Typography style={{ color: '#475569', fontSize: '1rem' }}>/100</Typography>
        </Box>

        <Box display="flex" justifyContent="center" mb={2}>
          <Chip
            label={`${cls.emoji} ${cls.label}`}
            className={classes.badge}
            style={{
              background: `${cls.color}22`,
              color: cls.color,
              border: `1px solid ${cls.color}`,
            }}
          />
        </Box>

        <Box className={classes.severityRow}>
          <Chip
            label={`🔴 ${scores.critical_violations} Critical`}
            size="small"
            className={classes.sevChip}
            style={{ background: '#fef2f2', color: '#ef4444' }}
          />
          <Chip
            label={`🟠 ${scores.high_violations} High`}
            size="small"
            className={classes.sevChip}
            style={{ background: '#fff7ed', color: '#f97316' }}
          />
        </Box>

        <Box display="flex" justifyContent="center" gap={1} flexWrap="wrap">
          <Chip
            label={`✅ ${scores.total_passed} Passed`}
            size="small"
            className={classes.sevChip}
            style={{ background: '#f0fdf4', color: '#22c55e' }}
          />
          <Chip
            label={`❌ ${scores.total_failed} Failed`}
            size="small"
            className={classes.sevChip}
            style={{ background: '#fafafa', color: '#64748b' }}
          />
        </Box>
      </CardContent>
      <CardActions style={{ justifyContent: 'center', paddingTop: 0 }}>
        <Button size="small" href="/compliance" className={classes.viewBtn}>
          View Details →
        </Button>
      </CardActions>
    </Card>
  );
}
