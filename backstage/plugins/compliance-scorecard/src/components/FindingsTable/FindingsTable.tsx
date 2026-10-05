/**
 * FindingsTable — sortable, filterable findings table.
 *
 * Displays findings from all 3 sources (Kyverno, Trivy, kube-bench)
 * with severity badges, status indicators and click-to-select for recommendations.
 */

import React, { useState, useMemo } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  CircularProgress,
} from '@material-ui/core';
import type { Finding } from '../../api/ComplianceApi';

const SEVERITY_CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  critical: { label: '🔴 Critical', bg: '#fef2f2', color: '#ef4444' },
  high:     { label: '🟠 High',     bg: '#fff7ed', color: '#f97316' },
  medium:   { label: '🟡 Medium',   bg: '#fefce8', color: '#ca8a04' },
  low:      { label: '🔵 Low',      bg: '#eff6ff', color: '#3b82f6' },
  info:     { label: '⚪ Info',     bg: '#f8fafc', color: '#94a3b8' },
};

const SOURCE_LABELS: Record<string, string> = {
  kyverno: 'Kyverno',
  trivy: 'Trivy',
  'kube-bench': 'kube-bench',
};

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  fail: { label: 'FAIL', color: '#ef4444' },
  pass: { label: 'PASS', color: '#22c55e' },
  warn: { label: 'WARN', color: '#f59e0b' },
  skip: { label: 'SKIP', color: '#94a3b8' },
};

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

const useStyles = makeStyles(theme => ({
  root: { padding: theme.spacing(2) },
  toolbar: {
    display: 'flex',
    gap: theme.spacing(2),
    alignItems: 'center',
    marginBottom: theme.spacing(2),
    flexWrap: 'wrap',
  },
  title: { fontWeight: 600, flex: 1 },
  filterControl: { minWidth: 140 },
  tableContainer: {
    maxHeight: 360,
    border: '1px solid #334155',
    borderRadius: 8,
    overflow: 'auto',
  },
  thead: { background: '#0f172a' },
  thCell: { color: '#94a3b8', fontWeight: 600, fontSize: '0.78rem' },
  row: {
    cursor: 'pointer',
    transition: 'background 0.15s',
    '&:hover': { background: '#1e293b' },
  },
  selectedRow: { background: '#1e3a5f !important' },
  severityChip: { fontSize: '0.72rem', fontWeight: 600, height: 22 },
  resourceText: { fontSize: '0.78rem', color: '#94a3b8' },
  titleText: { fontSize: '0.82rem', maxWidth: 280 },
}));

type SortKey = 'severity' | 'source' | 'status' | 'title';

interface Props {
  findings: Finding[];
  loading?: boolean;
  onSelect?: (finding: Finding) => void;
  selectedId?: string;
}

export function FindingsTable({ findings, loading, onSelect, selectedId }: Props) {
  const classes = useStyles();
  const [sortKey, setSortKey] = useState<SortKey>('severity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const filtered = useMemo(() => {
    let items = [...findings];
    if (severityFilter !== 'all') items = items.filter(f => f.severity === severityFilter);
    if (sourceFilter !== 'all') items = items.filter(f => f.source === sourceFilter);
    return items.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'severity') {
        cmp = SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity);
      } else {
        cmp = String(a[sortKey]).localeCompare(String(b[sortKey]));
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [findings, severityFilter, sourceFilter, sortKey, sortDir]);

  const failCount = findings.filter(f => f.status === 'fail').length;

  return (
    <Box className={classes.root}>
      <Box className={classes.toolbar}>
        <Typography variant="subtitle1" className={classes.title}>
          🔍 Findings ({failCount} failed / {findings.length} total)
        </Typography>
        <FormControl variant="outlined" size="small" className={classes.filterControl}>
          <InputLabel>Severity</InputLabel>
          <Select value={severityFilter} onChange={e => setSeverityFilter(e.target.value as string)} label="Severity">
            <MenuItem value="all">All</MenuItem>
            {SEVERITY_ORDER.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl variant="outlined" size="small" className={classes.filterControl}>
          <InputLabel>Source</InputLabel>
          <Select value={sourceFilter} onChange={e => setSourceFilter(e.target.value as string)} label="Source">
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="kyverno">Kyverno</MenuItem>
            <MenuItem value="trivy">Trivy</MenuItem>
            <MenuItem value="kube-bench">kube-bench</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}><CircularProgress /></Box>
      ) : (
        <TableContainer className={classes.tableContainer}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow className={classes.thead}>
                {(['severity', 'source', 'status', 'title'] as SortKey[]).map(key => (
                  <TableCell key={key} className={classes.thCell}>
                    <TableSortLabel
                      active={sortKey === key}
                      direction={sortKey === key ? sortDir : 'asc'}
                      onClick={() => handleSort(key)}
                      style={{ color: '#94a3b8' }}
                    >
                      {key.charAt(0).toUpperCase() + key.slice(1)}
                    </TableSortLabel>
                  </TableCell>
                ))}
                <TableCell className={classes.thCell}>Resource</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map(f => {
                const sev = SEVERITY_CONFIG[f.severity] ?? SEVERITY_CONFIG.info;
                const st = STATUS_CONFIG[f.status] ?? { label: f.status, color: '#94a3b8' };
                return (
                  <TableRow
                    key={f.finding_id}
                    className={`${classes.row} ${f.finding_id === selectedId ? classes.selectedRow : ''}`}
                    onClick={() => onSelect?.(f)}
                  >
                    <TableCell>
                      <Chip
                        label={sev.label}
                        size="small"
                        className={classes.severityChip}
                        style={{ background: sev.bg, color: sev.color, border: `1px solid ${sev.color}` }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" style={{ color: '#64748b' }}>
                        {SOURCE_LABELS[f.source] ?? f.source}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" style={{ color: st.color, fontWeight: 600 }}>
                        {st.label}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={f.description} placement="top-start">
                        <Typography variant="body2" className={classes.titleText} noWrap>
                          {f.title}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" className={classes.resourceText} noWrap>
                        {f.resource.kind}/{f.resource.name}
                        {f.resource.namespace && ` (${f.resource.namespace})`}
                      </Typography>
                    </TableCell>
                  </TableRow>
                );
              })}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} align="center" style={{ color: '#64748b', padding: 24 }}>
                    No findings match filters
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
