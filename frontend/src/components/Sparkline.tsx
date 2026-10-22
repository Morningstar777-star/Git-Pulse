import React from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 120,
  height = 34,
  color = '#38bdf8',
  className = ''
}) => {
  if (!data || data.length < 2) {
    return <div className="h-8 w-24 bg-white/5 rounded animate-pulse" />;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const paddingY = 4;
  const usableHeight = height - paddingY * 2;

  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * width;
    const y = height - paddingY - ((val - min) / range) * usableHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  const areaD = `${pathD} L ${width},${height} L 0,${height} Z`;
  const lastPoint = points[points.length - 1].split(',');

  const isUpward = data[data.length - 1] >= data[0];
  const strokeColor = color || (isUpward ? '#38bdf8' : '#94a3b8');
  const gradientId = `spark-grad-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <svg
      width={width}
      height={height}
      className={`overflow-visible ${className}`}
      viewBox={`0 0 ${width} ${height}`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.35" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
        </linearGradient>
      </defs>

      {/* Gradient Fill Area */}
      <path d={areaD} fill={`url(#${gradientId})`} />

      {/* Stroke Line */}
      <path
        d={pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* End Point Glow */}
      <circle
        cx={lastPoint[0]}
        cy={lastPoint[1]}
        r="3"
        fill={strokeColor}
        className="animate-pulse"
      />
    </svg>
  );
};
