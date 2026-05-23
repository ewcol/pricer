import styles from './TrackedTable.module.css';

export interface TrackedItem {
  item_id: string;
  title: string;
  recommended_price: number;
  current_market_price: number;
  price_drift_pct: number;
  listed_at: string;
}

interface Props {
  items: TrackedItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

function driftClass(drift: number): string {
  if (drift >= 5) return styles.driftUp;
  if (drift <= -10) return styles.driftDown;
  return styles.driftNeutral;
}

function driftLabel(drift: number): string {
  if (drift === 0) return '—';
  return drift > 0 ? `+${drift.toFixed(1)}%` : `${drift.toFixed(1)}%`;
}

export default function TrackedTable({ items, selectedId, onSelect }: Props) {
  if (items.length === 0) {
    return (
      <div className={styles.wrapper}>
        <table className={styles.table}>
          <thead>
            <tr className={styles.thead}>
              <th>Item ID</th><th>Title</th><th>Listed</th><th>Market</th><th>Drift</th><th>Listed At</th>
            </tr>
          </thead>
        </table>
        <div className={styles.empty}>
          <p className={styles.emptyText}>No tracked items yet.</p>
          <p className={styles.emptySub}>Analyze an item in Price &amp; List, then paste your eBay Item ID to start tracking.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr className={styles.thead}>
            <th>Item ID</th>
            <th>Title</th>
            <th>Listed</th>
            <th>Market</th>
            <th>Drift</th>
            <th>Listed At</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.item_id}
              className={`${styles.row} ${selectedId === item.item_id ? styles.rowSelected : ''}`}
              onClick={() => onSelect(item.item_id)}
              aria-selected={selectedId === item.item_id}
            >
              <td className={styles.mono}>{item.item_id}</td>
              <td><div className={styles.title}>{item.title}</div></td>
              <td className={styles.mono}>${item.recommended_price.toFixed(2)}</td>
              <td className={styles.mono}>
                {item.current_market_price > 0 ? `$${item.current_market_price.toFixed(2)}` : '—'}
              </td>
              <td className={`${styles.mono} ${driftClass(item.price_drift_pct)}`}>
                {driftLabel(item.price_drift_pct)}
              </td>
              <td className={styles.mono}>{formatDate(item.listed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
