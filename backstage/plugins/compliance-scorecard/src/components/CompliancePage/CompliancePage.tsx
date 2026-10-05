/**
 * CompliancePage — Main compliance dashboard.
 *
 * Layout:
 *   1. AI Summary Panel (AI executive assessment)
 *   2. Score Overview + Domain Breakdown (side-by-side)
 *   3. Score Trend (line chart)
 *   4. Findings Table (sortable, filterable)
 *   5. Recommendation Panel (Rule + AI Basic + AI Enriched + Compare)
 */

import React, { useState } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import {
  Box,
  Grid,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Snackbar,
} from '@material-ui/core';
import RefreshIcon from '@material-ui/icons/Refresh';
import SecurityIcon from '@material-ui/icons/Security';
import { useScores } from '../../hooks/useScores';
import { useFindings } from '../../hooks/useFindings';
import { ScoreOverview } from '../ScoreOverview/ScoreOverview';
import { DomainBreakdown } from '../DomainBreakdown/DomainBreakdown';
import { FindingsTable } from '../FindingsTable/FindingsTable';
import { ScoreTrend } from '../ScoreTrend/ScoreTrend';
import { RecommendationPanel } from '../RecommendationPanel/RecommendationPanel';
import { AISummaryPanel } from '../AISummaryPanel/AISummaryPanel';
import { ComplianceClient } from '../../api/ComplianceClient';
import type { Finding } from '../../api/ComplianceApi';

const client = new ComplianceClient();

const useStyles = makeStyles(theme => ({
  root: {
    background: '#020817',
    minHeight: '100vh',
    padding: theme.spacing(3),
  },
  pageHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing(3),
  },
  pageTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1.5),
    color: '#f1f5f9',
    fontWeight: 700,
  },
  titleIcon: {
    color: '#6366f1',
    fontSize: 28,
  },
  scanBtn: {
    background: '#6366f1',
    color: '#fff',
    fontWeight: 600,
    borderRadius: 8,
    padding: theme.spacing(0.75, 2),
    '&:hover': { background: '#4f46e5' },
  },
  panel: {
    background: '#0f172a',
    border: '1px solid #1e293b',
    borderRadius: 12,
    height: '100%',
  },
  loadingCenter: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: 300,
    flexDirection: 'column',
    gap: theme.spacing(2),
  },
  errorText: {
    color: '#f87171',
    textAlign: 'center' as const,
    padding: theme.spacing(4),
  },
}));

export function CompliancePage() {
  const classes = useStyles();
  const { scores, history, loading: scoresLoading, error: scoresError, refresh: refreshScores } = useScores();
  const { data: findingsData, loading: findingsLoading, error: findingsError, setFilters, refresh: refreshFindings } = useFindings();
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [scanning, setScanning] = useState(false);
  const [snackMsg, setSnackMsg] = useState('');

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await client.triggerScan();
      setSnackMsg(`✅ Scan triggered (ID: ${result.scan_id}). Results in ~30s.`);
      setTimeout(() => { refreshScores(); refreshFindings(); }, 5000);
    } catch (e: any) {
      setSnackMsg(`❌ Scan failed: ${e?.message}`);
    } finally {
      setScanning(false);
    }
  };

  if (scoresLoading) {
    return (
      <Box className={classes.root}>
        <Box className={classes.loadingCenter}>
          <CircularProgress style={{ color: '#6366f1' }} size={48} />
          <Typography style={{ color: '#94a3b8' }}>Loading compliance data...</Typography>
        </Box>
      </Box>
    );
  }

  if (scoresError) {
    return (
      <Box className={classes.root}>
        <Typography className={classes.errorText}>
          ⚠️ Failed to load compliance data: {scoresError}
        </Typography>
        <Box display="flex" justifyContent="center">
          <Button onClick={refreshScores} style={{ color: '#6366f1' }}>Retry</Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box className={classes.root}>
      {/* Page Header */}
      <Box className={classes.pageHeader}>
        <Box className={classes.pageTitle}>
          <SecurityIcon className={classes.titleIcon} />
          <Box>
            <Typography variant="h5" style={{ color: '#f1f5f9', fontWeight: 700 }}>
              Compliance Scorecard
            </Typography>
            <Typography variant="caption" style={{ color: '#64748b' }}>
              Kubernetes security posture — Kyverno · Trivy · kube-bench
            </Typography>
          </Box>
        </Box>
        <Button
          variant="contained"
          className={classes.scanBtn}
          startIcon={scanning ? <CircularProgress size={16} style={{ color: '#fff' }} /> : <RefreshIcon />}
          onClick={handleScan}
          disabled={scanning}
        >
          {scanning ? 'Scanning...' : '🔄 Scan Now'}
        </Button>
      </Box>

      {/* AI Summary Panel */}
      <AISummaryPanel />

      {/* Score Overview + Domain Breakdown */}
      {scores && (
        <Grid container spacing={2} style={{ marginBottom: 16 }}>
          <Grid item xs={12} md={4}>
            <Paper className={classes.panel}>
              <ScoreOverview scores={scores} />
            </Paper>
          </Grid>
          <Grid item xs={12} md={8}>
            <Paper className={classes.panel}>
              <DomainBreakdown domains={scores.domains} />
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Score Trend */}
      {history.length > 0 && (
        <Paper className={classes.panel} style={{ marginBottom: 16 }}>
          <ScoreTrend history={history} />
        </Paper>
      )}

      {/* Findings Table */}
      <Paper className={classes.panel} style={{ marginBottom: 16 }}>
        <FindingsTable
          findings={findingsData?.items ?? []}
          loading={findingsLoading}
          onSelect={setSelectedFinding}
          selectedId={selectedFinding?.finding_id}
        />
      </Paper>

      {/* Recommendation Panel */}
      <RecommendationPanel finding={selectedFinding} />

      {/* Scan result snackbar */}
      <Snackbar
        open={!!snackMsg}
        autoHideDuration={6000}
        onClose={() => setSnackMsg('')}
        message={snackMsg}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      />
    </Box>
  );
}
