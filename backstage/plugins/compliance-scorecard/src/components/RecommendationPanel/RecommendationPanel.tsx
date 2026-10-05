/**
 * RecommendationPanel — Rule-based, AI Basic, AI Enriched tabs + Compare view.
 *
 * For thesis experiment: shows all 3 approaches side-by-side with
 * latency, confidence, and CIS references for comparison.
 */

import React, { useState } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  CircularProgress,
  Button,
  Chip,
  Divider,
  Paper,
} from '@material-ui/core';
import CompareArrowsIcon from '@material-ui/icons/CompareArrows';
import type { Finding, RuleRecommendation, AIRecommendation } from '../../api/ComplianceApi';
import { ComplianceClient } from '../../api/ComplianceClient';

const client = new ComplianceClient();

const useStyles = makeStyles(theme => ({
  root: {
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 12,
    padding: theme.spacing(2.5),
  },
  title: {
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: theme.spacing(1.5),
  },
  tabs: {
    marginBottom: theme.spacing(2),
    borderBottom: '1px solid #1e293b',
    '& .MuiTab-root': { color: '#64748b', minWidth: 100, fontSize: '0.8rem' },
    '& .Mui-selected': { color: '#6366f1' },
  },
  indicator: { backgroundColor: '#6366f1' },
  section: {
    background: '#1e293b',
    borderRadius: 8,
    padding: theme.spacing(2),
    marginBottom: theme.spacing(1.5),
  },
  label: {
    fontSize: '0.72rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 1,
    color: '#64748b',
    marginBottom: theme.spacing(0.5),
  },
  value: {
    color: '#e2e8f0',
    fontSize: '0.85rem',
    lineHeight: 1.6,
  },
  code: {
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: theme.spacing(1.5),
    fontFamily: 'monospace',
    fontSize: '0.78rem',
    color: '#7dd3fc',
    overflow: 'auto',
    maxHeight: 200,
    whiteSpace: 'pre',
  },
  badge: {
    fontSize: '0.7rem',
    height: 22,
    marginRight: theme.spacing(0.5),
    marginBottom: theme.spacing(0.5),
  },
  compareGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: theme.spacing(1.5),
    [theme.breakpoints.down('sm')]: {
      gridTemplateColumns: '1fr',
    },
  },
  compareCard: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: theme.spacing(1.5),
  },
  compareTitle: {
    fontSize: '0.8rem',
    fontWeight: 700,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: theme.spacing(1),
    borderBottom: '1px solid #334155',
    paddingBottom: theme.spacing(0.5),
  },
  latencyBadge: {
    display: 'inline-block',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 4,
    padding: '2px 8px',
    fontSize: '0.7rem',
    color: '#6366f1',
    fontFamily: 'monospace',
  },
  emptyState: {
    color: '#475569',
    textAlign: 'center' as const,
    padding: theme.spacing(4),
  },
}));

interface TabPanelProps {
  children?: React.ReactNode;
  value: number;
  index: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return <div hidden={value !== index}>{value === index && children}</div>;
}

interface Props {
  finding: Finding | null;
}

export function RecommendationPanel({ finding }: Props) {
  const classes = useStyles();
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [ruleRec, setRuleRec] = useState<RuleRecommendation | null>(null);
  const [basicRec, setBasicRec] = useState<AIRecommendation | null>(null);
  const [enrichedRec, setEnrichedRec] = useState<AIRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRule = async () => {
    if (!finding) return;
    setLoading(true); setError(null);
    try { setRuleRec(await client.getRuleRecommendation(finding.finding_id)); }
    catch (e: any) { setError(e?.message); }
    finally { setLoading(false); }
  };

  const loadAI = async (strategy: 'basic' | 'context_enriched') => {
    if (!finding) return;
    setLoading(true); setError(null);
    try {
      const rec = await client.getAIRecommendation(finding.finding_id, strategy);
      if (strategy === 'basic') setBasicRec(rec);
      else setEnrichedRec(rec);
    } catch (e: any) { setError(e?.message); }
    finally { setLoading(false); }
  };

  const loadCompare = async () => {
    if (!finding) return;
    setLoading(true); setError(null);
    try {
      const { basic, context_enriched } = await client.compareRecommendations(finding.finding_id);
      setBasicRec(basic);
      setEnrichedRec(context_enriched);
    } catch (e: any) { setError(e?.message); }
    finally { setLoading(false); }
  };

  if (!finding) {
    return (
      <Box className={classes.root}>
        <Typography variant="subtitle1" className={classes.title}>💡 Recommendation Panel</Typography>
        <Typography className={classes.emptyState}>
          Select a finding from the table above to see recommendations.
        </Typography>
      </Box>
    );
  }

  return (
    <Box className={classes.root}>
      <Typography variant="subtitle1" className={classes.title}>
        💡 Recommendation for: <span style={{ color: '#6366f1' }}>{finding.finding_id}</span>
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        className={classes.tabs}
        TabIndicatorProps={{ className: classes.indicator }}
      >
        <Tab label="📋 Rule-based" />
        <Tab label="🤖 AI Basic" />
        <Tab label="🧠 AI Enriched" />
        <Tab label={<Box display="flex" alignItems="center" gap={0.5}><CompareArrowsIcon style={{ fontSize: 16 }} /> Compare</Box>} />
      </Tabs>

      {loading && (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress size={28} style={{ color: '#6366f1' }} />
        </Box>
      )}

      {error && (
        <Typography style={{ color: '#f87171', fontSize: '0.82rem', marginBottom: 12 }}>
          ⚠️ {error}
        </Typography>
      )}

      {/* Rule-based tab */}
      <TabPanel value={tab} index={0}>
        {!ruleRec ? (
          <Button variant="outlined" size="small" onClick={loadRule} style={{ borderColor: '#334155', color: '#94a3b8' }}>
            Load Rule-based Recommendation
          </Button>
        ) : (
          <>
            <Box className={classes.section}>
              <Typography className={classes.label}>Fix</Typography>
              <Typography className={classes.value}>{ruleRec.fix}</Typography>
            </Box>
            <Box className={classes.section}>
              <Typography className={classes.label}>Policy Reference</Typography>
              <Typography className={classes.value}>{ruleRec.reference}</Typography>
            </Box>
            <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
              <span className={classes.latencyBadge}>⚡ {ruleRec.latency_ms.toFixed(2)}ms</span>
              <Chip label={`Severity: ${ruleRec.severity}`} size="small" className={classes.badge} style={{ background: '#1e293b', color: '#94a3b8' }} />
            </Box>
          </>
        )}
      </TabPanel>

      {/* AI Basic tab */}
      <TabPanel value={tab} index={1}>
        {!basicRec ? (
          <Button variant="outlined" size="small" onClick={() => loadAI('basic')} style={{ borderColor: '#334155', color: '#94a3b8' }}>
            Load AI Basic Recommendation
          </Button>
        ) : (
          <AIRecView rec={basicRec} classes={classes} />
        )}
      </TabPanel>

      {/* AI Enriched tab */}
      <TabPanel value={tab} index={2}>
        {!enrichedRec ? (
          <Button variant="outlined" size="small" onClick={() => loadAI('context_enriched')} style={{ borderColor: '#334155', color: '#94a3b8' }}>
            Load AI Enriched Recommendation
          </Button>
        ) : (
          <AIRecView rec={enrichedRec} classes={classes} />
        )}
      </TabPanel>

      {/* Compare tab */}
      <TabPanel value={tab} index={3}>
        {!basicRec && !enrichedRec ? (
          <Button
            variant="outlined"
            size="small"
            startIcon={<CompareArrowsIcon />}
            onClick={loadCompare}
            style={{ borderColor: '#6366f1', color: '#6366f1' }}
          >
            Run 3-way Comparison
          </Button>
        ) : (
          <Box className={classes.compareGrid}>
            {/* Rule-based column */}
            <Box className={classes.compareCard}>
              <Typography className={classes.compareTitle}>📋 Rule-based</Typography>
              {ruleRec ? (
                <>
                  <Typography style={{ color: '#e2e8f0', fontSize: '0.82rem', marginBottom: 8 }}>{ruleRec.fix}</Typography>
                  <Typography style={{ color: '#64748b', fontSize: '0.75rem' }}>Ref: {ruleRec.reference}</Typography>
                  <Box mt={1}><span className={classes.latencyBadge}>⚡ {ruleRec.latency_ms.toFixed(2)}ms</span></Box>
                </>
              ) : (
                <Typography style={{ color: '#475569', fontSize: '0.8rem' }}>
                  Load Rule-based tab first
                </Typography>
              )}
            </Box>

            {/* AI Basic column */}
            <Box className={classes.compareCard}>
              <Typography className={classes.compareTitle}>🤖 AI Basic</Typography>
              {basicRec && (
                <>
                  <Typography style={{ color: '#e2e8f0', fontSize: '0.82rem', marginBottom: 8 }}>{basicRec.root_cause}</Typography>
                  <Chip label={`Confidence: ${(basicRec.confidence * 100).toFixed(0)}%`} size="small" className={classes.badge} style={{ background: '#1e293b', color: '#94a3b8' }} />
                  <Box mt={1}><span className={classes.latencyBadge}>⏱ {basicRec.latency_ms.toFixed(0)}ms</span></Box>
                </>
              )}
            </Box>

            {/* AI Enriched column */}
            <Box className={classes.compareCard}>
              <Typography className={classes.compareTitle}>🧠 AI Enriched</Typography>
              {enrichedRec && (
                <>
                  <Typography style={{ color: '#e2e8f0', fontSize: '0.82rem', marginBottom: 8 }}>{enrichedRec.root_cause}</Typography>
                  <Chip label={`Confidence: ${(enrichedRec.confidence * 100).toFixed(0)}%`} size="small" className={classes.badge} style={{ background: '#1e293b', color: '#94a3b8' }} />
                  <Box mt={1}><span className={classes.latencyBadge}>⏱ {enrichedRec.latency_ms.toFixed(0)}ms</span></Box>
                </>
              )}
            </Box>
          </Box>
        )}
      </TabPanel>
    </Box>
  );
}

interface AIRecViewProps {
  rec: AIRecommendation;
  classes: ReturnType<typeof useStyles>;
}

function AIRecView({ rec, classes }: AIRecViewProps) {
  const urgencyColors: Record<string, string> = {
    immediate: '#ef4444',
    soon: '#f97316',
    low: '#22c55e',
  };
  return (
    <>
      <Box className={classes.section}>
        <Typography className={classes.label}>Root Cause</Typography>
        <Typography className={classes.value}>{rec.root_cause}</Typography>
      </Box>
      <Box className={classes.section}>
        <Typography className={classes.label}>YAML Fix</Typography>
        <pre className={classes.code}>{rec.yaml_fix}</pre>
      </Box>
      <Box className={classes.section}>
        <Typography className={classes.label}>Impact if Unfixed</Typography>
        <Typography className={classes.value}>{rec.impact_if_unfixed}</Typography>
      </Box>
      <Box className={classes.section}>
        <Typography className={classes.label}>CIS References</Typography>
        <Box display="flex" flexWrap="wrap">
          {rec.cis_references.map(ref => (
            <Chip key={ref} label={`CIS ${ref}`} size="small" className={classes.badge} style={{ background: '#1e3a5f', color: '#7dd3fc' }} />
          ))}
        </Box>
      </Box>
      <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
        <span className={classes.latencyBadge}>⏱ {rec.latency_ms.toFixed(0)}ms</span>
        <Chip
          label={`Urgency: ${rec.urgency}`}
          size="small"
          className={classes.badge}
          style={{ background: `${urgencyColors[rec.urgency] ?? '#94a3b8'}22`, color: urgencyColors[rec.urgency] ?? '#94a3b8' }}
        />
        <Chip
          label={`Confidence: ${(rec.confidence * 100).toFixed(0)}%`}
          size="small"
          className={classes.badge}
          style={{ background: '#1e293b', color: '#94a3b8' }}
        />
      </Box>
    </>
  );
}
