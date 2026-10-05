/**
 * AISummaryPanel — AI Executive Security Assessment widget.
 *
 * Shows Gemini-generated security posture summary with:
 * - Risk level badge
 * - Overall assessment narrative
 * - Top 3 priority fixes with effort estimates
 * - Remediation roadmap (Immediate / Sprint / Backlog)
 */

import React, { useEffect, useState } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import {
  Box,
  Typography,
  Chip,
  CircularProgress,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@material-ui/core';
import ExpandMoreIcon from '@material-ui/icons/ExpandMore';
import RefreshIcon from '@material-ui/icons/Refresh';
import type { AISummaryResponse } from '../../api/ComplianceApi';
import { ComplianceClient } from '../../api/ComplianceClient';

const client = new ComplianceClient();

const RISK_CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  critical: { label: '🔴 CRITICAL', bg: '#fef2f2', color: '#ef4444' },
  high:     { label: '🟠 HIGH',     bg: '#fff7ed', color: '#f97316' },
  moderate: { label: '🟡 MODERATE', bg: '#fefce8', color: '#ca8a04' },
  low:      { label: '🟢 LOW',      bg: '#f0fdf4', color: '#22c55e' },
};

const TREND_CONFIG: Record<string, string> = {
  improving: '📈 Improving',
  stable: '➡️ Stable',
  declining: '📉 Declining',
};

const PHASE_CONFIG: Record<string, { label: string; color: string }> = {
  immediate:   { label: '🚨 Immediate', color: '#ef4444' },
  this_sprint: { label: '🏃 This Sprint', color: '#f97316' },
  backlog:     { label: '📋 Backlog', color: '#3b82f6' },
};

const useStyles = makeStyles(theme => ({
  root: {
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    border: '1px solid #334155',
    borderRadius: 12,
    padding: theme.spacing(2.5),
    marginBottom: theme.spacing(2),
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing(2),
  },
  headerTitle: {
    fontWeight: 700,
    color: '#f1f5f9',
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
  },
  assessment: {
    color: '#cbd5e1',
    fontSize: '0.88rem',
    lineHeight: 1.6,
    fontStyle: 'italic',
    marginBottom: theme.spacing(2),
    borderLeft: '3px solid #6366f1',
    paddingLeft: theme.spacing(1.5),
  },
  priorityItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: theme.spacing(1.5),
    padding: theme.spacing(1),
    borderRadius: 6,
    background: '#ffffff08',
    marginBottom: theme.spacing(0.5),
  },
  effortBadge: {
    fontSize: '0.7rem',
    height: 20,
    background: '#1e293b',
    color: '#94a3b8',
    border: '1px solid #334155',
  },
  phaseRow: {
    display: 'flex',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
    marginBottom: theme.spacing(1),
  },
  accordion: {
    background: 'transparent',
    boxShadow: 'none',
    '&:before': { display: 'none' },
  },
  accordionSummary: { padding: 0, minHeight: '36px !important' },
  accordionDetails: { padding: theme.spacing(0, 0, 1) },
  latency: {
    fontSize: '0.7rem',
    color: '#475569',
    marginTop: theme.spacing(1),
    textAlign: 'right',
  },
}));

export function AISummaryPanel() {
  const classes = useStyles();
  const [summary, setSummary] = useState<AISummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await client.getAISummary();
      setSummary(data);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load AI summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <Box className={classes.root} display="flex" justifyContent="center" alignItems="center" minHeight={120}>
        <CircularProgress size={32} style={{ color: '#6366f1' }} />
        <Typography style={{ color: '#94a3b8', marginLeft: 12 }}>Generating AI assessment...</Typography>
      </Box>
    );
  }

  if (error || !summary) {
    return (
      <Box className={classes.root}>
        <Typography style={{ color: '#f87171' }}>
          🤖 AI Summary unavailable: {error ?? 'No data'}
        </Typography>
        <Button size="small" onClick={load} style={{ color: '#6366f1', marginTop: 8 }}>
          Retry
        </Button>
      </Box>
    );
  }

  const risk = RISK_CONFIG[summary.risk_level] ?? RISK_CONFIG.moderate;

  return (
    <Box className={classes.root}>
      {/* Header */}
      <Box className={classes.header}>
        <Typography variant="subtitle1" className={classes.headerTitle}>
          🤖 AI Security Assessment
        </Typography>
        <Box display="flex" alignItems="center" gap={1}>
          <Chip
            label={risk.label}
            size="small"
            style={{ background: `${risk.color}22`, color: risk.color, fontWeight: 700, border: `1px solid ${risk.color}` }}
          />
          <Typography variant="caption" style={{ color: '#475569' }}>
            {TREND_CONFIG[summary.trend_prediction] ?? summary.trend_prediction}
          </Typography>
          <Button
            size="small"
            startIcon={<RefreshIcon style={{ fontSize: 14 }} />}
            onClick={load}
            style={{ color: '#6366f1', minWidth: 'auto', padding: '2px 8px' }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Assessment narrative */}
      <Typography className={classes.assessment}>
        "{summary.overall_assessment}"
      </Typography>

      {/* Top priorities */}
      <Typography variant="caption" style={{ color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
        🎯 Top Priorities
      </Typography>
      <Box mt={1} mb={2}>
        {summary.top_priorities.map((p, i) => {
          const sevConfig = {
            critical: { icon: '🔴', color: '#ef4444' },
            high: { icon: '🟠', color: '#f97316' },
            medium: { icon: '🟡', color: '#ca8a04' },
            low: { icon: '🔵', color: '#3b82f6' },
          }[p.severity] ?? { icon: '⚪', color: '#94a3b8' };
          return (
            <Box key={p.finding_id} className={classes.priorityItem}>
              <Typography style={{ fontSize: '0.85rem', color: '#94a3b8', minWidth: 18 }}>{i + 1}.</Typography>
              <Box flex={1}>
                <Typography variant="body2" style={{ color: '#e2e8f0', fontWeight: 500 }}>
                  {sevConfig.icon} {p.title}
                </Typography>
                <Typography variant="caption" style={{ color: '#94a3b8' }}>{p.fix_summary}</Typography>
              </Box>
              <Chip label={`⏱ ${p.estimated_effort}`} size="small" className={classes.effortBadge} />
            </Box>
          );
        })}
      </Box>

      <Divider style={{ background: '#1e293b', marginBottom: 12 }} />

      {/* Remediation roadmap */}
      <Accordion className={classes.accordion}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon style={{ color: '#94a3b8', fontSize: 18 }} />}
          className={classes.accordionSummary}
        >
          <Typography variant="caption" style={{ color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
            📋 Remediation Roadmap
          </Typography>
        </AccordionSummary>
        <AccordionDetails className={classes.accordionDetails}>
          <Box className={classes.phaseRow}>
            {summary.remediation_phases.map(phase => {
              const ph = PHASE_CONFIG[phase.phase] ?? { label: phase.phase, color: '#94a3b8' };
              return (
                <Chip
                  key={phase.phase}
                  label={`${ph.label} (${phase.finding_ids.length} fixes · ${phase.total_estimated_effort})`}
                  size="small"
                  style={{ background: `${ph.color}22`, color: ph.color, border: `1px solid ${ph.color}`, fontSize: '0.75rem' }}
                />
              );
            })}
          </Box>
        </AccordionDetails>
      </Accordion>

      <Typography className={classes.latency}>
        Generated {new Date(summary.generated_at).toLocaleString()} · {summary.latency_ms.toFixed(0)}ms
      </Typography>
    </Box>
  );
}
