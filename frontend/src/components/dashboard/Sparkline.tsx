import React from 'react';

interface SparklineProps {
  data: number[];
  up: boolean;
}

const Sparkline: React.FC<SparklineProps> = ({ data, up }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const H = 32;
  const W = 56;
  const step = W / (data.length - 1);
  const pts = data
    .map((v, i) => `${i * step},${H - ((v - min) / range) * H}`)
    .join(' ');
  return (
    <svg width={W} height={H} className="opacity-60">
      <polyline
        points={pts}
        fill="none"
        stroke={up ? '#10b981' : '#f97316'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default Sparkline;
