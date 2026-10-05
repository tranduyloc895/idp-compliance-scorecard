/**
 * DomainBreakdown — 4-domain horizontal bar chart using Recharts.
 *
 * Shows Cluster Security, Workload Security, Supply Chain, Platform Config
 * scores side-by-side with color-coded bars.
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { makeStyles } from '@material-ui/core/styles';
import { Box, Typography } from '@material-ui/core';
import type { DomainScore } from '../../api/ComplianceApi';

const DOMAIN_LABELS: Record<string, string> = {
  cluster_security: 'Cluster Security',
  workload_security: 'Workload Security',
  supply_chain: 'Supply Chain',
  platform_config: 'Platform Config',
};

const useStyles = makeStyles(theme => ({
  root: {
    padding: theme.spacing(2),
  },
  title: {
    fontWeight: 600,
    marginBottom: theme.spacing(2),
  },
}));

function getBarColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 75) return '#3b82f6';
  if (score >= 60) return '#f59e0b';
  return '#ef4444';
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as DomainScore & { name: string };
  return (
    <Box
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: '10px 14px',
        color: '#f1f5f9',
        fontSize: '0.82rem',
      }}
    >
      <Typography variant="subtitle2" style={{ color: '#94a3b8', marginBottom: 4 }}>
        {label}
      </Typography>
      <div>Score: <strong style={{ color: getBarColor(d.score) }}>{d.score.toFixed(1)}</strong></div>
      <div>Weight: {(d.weight * 100).toFixed(0)}%</div>
      <div>Passed: {d.passed}/{d.total_checks}</div>
      <div>Critical: {d.critical_count} | High: {d.high_count}</div>
    </Box>
  );
}

interface Props {
  domains: DomainScore[];
}

export function DomainBreakdown({ domains }: Props) {
  const classes = useStyles();

  const data = domains.map(d => ({
    ...d,
    name: DOMAIN_LABELS[d.domain] ?? d.domain,
    score: Math.round(d.score * 10) / 10,
  }));

  return (
    <Box className={classes.root}>
      <Typography variant="subtitle1" className={classes.title}>
        Domain Breakdown
      </Typography>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 40, left: 10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            width={120}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#334155', opacity: 0.3 }} />
          <ReferenceLine x={75} stroke="#3b82f6" strokeDasharray="4 4" label={{ value: 'Good', fill: '#3b82f6', fontSize: 10 }} />
          <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={24} label={{ position: 'right', fill: '#94a3b8', fontSize: 11, formatter: (v: number) => `${v}` }}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={getBarColor(entry.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
}
