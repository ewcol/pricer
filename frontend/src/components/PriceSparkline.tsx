import styles from './PriceSparkline.module.css';

export interface HistoryEntry {
  new_price: number;
  detected_at: string;
}

interface Props {
  data: HistoryEntry[];
}

const WIDTH = 50;
const HEIGHT = 24;
const PADDING = 2;

function trendClass(data: HistoryEntry[]): string {
  if (data.length < 2) return styles.flat;
  const first = data[0].new_price;
  const last = data[data.length - 1].new_price;
  if (last > first) return styles.up;
  if (last < first) return styles.down;
  return styles.flat;
}

export default function PriceSparkline({ data }: Props) {
  if (data.length < 2) {
    return <span className={styles.empty}>No history yet</span>;
  }

  const prices = data.map((point) => point.new_price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const step = (WIDTH - PADDING * 2) / (data.length - 1);
  const points = data.map((point, index) => {
    const x = PADDING + index * step;
    const normalized = (point.new_price - min) / range;
    const y = HEIGHT - PADDING - normalized * (HEIGHT - PADDING * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const lastPoint = data[data.length - 1];
  const lastIndex = data.length - 1;
  const lastX = PADDING + lastIndex * step;
  const lastNormalized = (lastPoint.new_price - min) / range;
  const lastY = HEIGHT - PADDING - lastNormalized * (HEIGHT - PADDING * 2);

  return (
    <div className={styles.wrap}>
      <svg
        className={`${styles.sparkline} ${trendClass(data)}`}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width={WIDTH}
        height={HEIGHT}
        aria-hidden="true"
      >
        <polyline className={styles.line} points={points} />
        <circle className={styles.dot} cx={lastX} cy={lastY} r="1.7" />
      </svg>
    </div>
  );
}
