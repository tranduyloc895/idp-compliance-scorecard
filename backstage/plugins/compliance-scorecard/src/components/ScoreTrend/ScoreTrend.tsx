/**
 * ScoreTrend — Line chart showing score history (Recharts).
 *
 * Displays overall score trend across last N scans with classification
 * threshold reference lines at 75 (Good) and 90 (Excellent).
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Dot,
} from 'recharts';
import { makeStyles } from '@material-ui/core/styles';
import { Box, Typography } from '@material-ui/core';
import type { ScoresResponse } from '../../api/ComplianceApi';

const useStyles = makeStyles(theme => ({
  root: {
    padding: theme.spacing(2),
  },
  title: {
    fontWeight: 600,
    marginBottom: theme.spacing(2),
  },
}));

function getScoreColor(score: number): string {
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
  const score = payload[0].value as number;
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
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      <div>
        Score:{' '}
        <strong style={{ color: getScoreColor(score), fontSize: '1rem' }}>
          {score.toFixed(1)}
        </strong>
      </div>
    </Box>
  );
}

interface CustomDotProps {
  cx?: number;
  cy?: number;
  payload?: { score: number };
}

function CustomDot({ cx, cy, payload }: CustomDotProps) {
  if (cx === undefined || cy === undefined || !payload) return null;
  return (
    <Dot
      cx={cx}
      cy={cy}
      r={5}
      fill={getScoreColor(payload.score)}
      stroke="#0f172a"
      strokeWidth={2}
    />
  );
}

interface Props {
  history: ScoresResponse[];
}

export function ScoreTrend({ history }: Props) {
  const classes = useStyles();

  const data = [...history]
    .reverse()
    .slice(-10)
    .map((s, i) => ({
      scan: `Scan ${i + 1}`,
      score: Math.round(s.overall_score * 10) / 10,
      classification: s.classification,
      date: new Date(s.scanned_at).toLocaleDateString(),
    }));

  if (data.length < 2) {
    return (
      <Box className={classes.root}>
        <Typography variant="subtitle1" className={classes.title}>📈 Score Trend</Typography>
        <Typography variant="body2" style={{ color: '#94a3b8' }}>
          Not enough scan history (need at least 2 scans).
        </Typography>
      </Box>
    );
  }

  return (
    <Box className={classes.root}>
      <Typography variant="subtitle1" className={classes.title}>
        📈 Score Trend (last {data.length} scans)
      </Typography>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="scan" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            width={35}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={90}
            stroke="#22c55e"
            strokeDasharray="4 4"
            label={{ value: 'Excellent', fill: '#22c55e', fontSize: 10, position: 'insideTopRight' }}
          />
          <ReferenceLine
            y={75}
            stroke="#3b82f6"
            strokeDasharray="4 4"
            label={{ value: 'Good', fill: '#3b82f6', fontSize: 10, position: 'insideTopRight' }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={<CustomDot />}
            activeDot={{ r: 7, fill: '#6366f1', stroke: '#0f172a', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
}
