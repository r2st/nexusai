'use client';

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts';
import type { BreakdownItem } from './types';

const COLORS = [
  '#22c55e', // green-500
  '#3b82f6', // blue-500
  '#8b5cf6', // violet-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#06b6d4', // cyan-500
  '#ec4899', // pink-500
  '#84cc16', // lime-500
];

const tooltipStyle: React.CSSProperties = {
  backgroundColor: 'rgba(15, 23, 42, 0.9)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '8px',
  fontSize: '12px',
  color: '#f8fafc',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
};

function formatCurrency(value: number): string {
  if (value >= 1) return `$${value.toFixed(2)}`;
  if (value >= 0.01) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(4)}`;
}

interface CostBreakdownPieProps {
  data: BreakdownItem[];
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
}

export function CostBreakdownPie({
  data,
  height = 300,
  innerRadius = 60,
  outerRadius = 100,
}: CostBreakdownPieProps) {
  // Transform data for the chart
  const chartData = data.map((item, index) => ({
    name: item.name,
    value: item.total_cost,
    percentage: item.percentage,
    tokens: item.total_tokens,
    requests: item.request_count,
    fill: COLORS[index % COLORS.length],
  }));

  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{
      payload: {
        name: string;
        value: number;
        percentage: number;
        tokens: number;
        requests: number;
      };
    }>;
  }) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload;
    return (
      <div style={tooltipStyle} className="p-3">
        <p className="font-medium mb-2">{data.name}</p>
        <div className="space-y-1 text-sm">
          <p>
            Cost: <span className="font-medium">{formatCurrency(data.value)}</span>
          </p>
          <p>
            Percentage: <span className="font-medium">{data.percentage.toFixed(1)}%</span>
          </p>
          <p>
            Tokens: <span className="font-medium">{data.tokens.toLocaleString()}</span>
          </p>
          <p>
            Requests: <span className="font-medium">{data.requests.toLocaleString()}</span>
          </p>
        </div>
      </div>
    );
  };

  const CustomLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
    name,
  }: {
    cx?: number;
    cy?: number;
    midAngle?: number;
    innerRadius?: number;
    outerRadius?: number;
    percent?: number;
    name?: string;
  }) => {
    if (!percent || !cx || !cy || !midAngle || !innerRadius || !outerRadius || percent < 0.05) return null;

    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 1.4;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="#94a3b8"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={11}
        fontFamily="ui-monospace, monospace"
      >
        {`${name} (${(percent * 100).toFixed(0)}%)`}
      </text>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          paddingAngle={2}
          dataKey="value"
          label={CustomLabel}
          labelLine={false}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}

// Horizontal bar variant for breakdown
export function CostBreakdownBars({
  data,
  maxItems = 5,
}: {
  data: BreakdownItem[];
  maxItems?: number;
}) {
  const items = data.slice(0, maxItems);
  const maxCost = Math.max(...items.map((i) => i.total_cost));

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const width = maxCost > 0 ? (item.total_cost / maxCost) * 100 : 0;
        return (
          <div key={item.name} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium truncate">{item.name}</span>
              <span className="text-muted-foreground ml-2">
                {formatCurrency(item.total_cost)} ({item.percentage.toFixed(1)}%)
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${width}%`,
                  backgroundColor: COLORS[index % COLORS.length],
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
