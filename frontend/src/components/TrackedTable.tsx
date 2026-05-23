import { useState } from 'react';
import PriceSparkline, { type HistoryEntry } from './PriceSparkline';
import { driftLabel, formatTrackedDate, thumbnailAlt } from './TrackedTable.helpers.js';
import styles from './TrackedTable.module.css';

export interface TrackedItem {
  item_id: string;
  title: string;
  recommended_price: number;
  image_url: string;
  current_market_price: number;
  price_drift_pct: number;
  listed_at: string;
}

interface Props {
  items: TrackedItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  historyMap: Record<string, HistoryEntry[]>;
}

function driftClass(drift: number): string {
  if (drift >= 5) return styles.driftUp;
  if (drift <= -10) return styles.driftDown;
  return styles.driftNeutral;
}

export default function TrackedTable({ items, selectedId, onSelect, historyMap }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className={styles.wrapper}>
        <table className={styles.table}>
          <thead>
            <tr className={styles.thead}>
              <th>Item</th>
              <th>Listed Price</th>
              <th>Market</th>
              <th>Drift</th>
              <th>Listed At</th>
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
            <th>Item</th>
            <th>Listed Price</th>
            <th>Market</th>
            <th>Drift</th>
            <th>Listed At</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const hasHistory = Object.prototype.hasOwnProperty.call(historyMap, item.item_id);
            const showHistory = hasHistory && (selectedId === item.item_id || hoveredId === item.item_id);

            return (
              <tr
                key={item.item_id}
                className={`${styles.row} ${selectedId === item.item_id ? styles.rowSelected : ''}`}
                onClick={() => onSelect(item.item_id)}
                onMouseEnter={() => setHoveredId(item.item_id)}
                onMouseLeave={() => setHoveredId(null)}
                aria-selected={selectedId === item.item_id}
              >
                <td>
                  <div className={styles.itemCell}>
                    {item.image_url ? (
                      <a
                        className={styles.thumbLink}
                        href={item.image_url}
                        target="_blank"
                        rel="noreferrer"
                        aria-label={`Open image for ${item.title}`}
                      >
                        <img
                          className={styles.thumb}
                          src={item.image_url}
                          alt={thumbnailAlt(item.title)}
                          loading="lazy"
                        />
                      </a>
                    ) : (
                      <div className={styles.thumbFallback} aria-hidden="true">
                        No image
                      </div>
                    )}
                    <div className={styles.itemCopy}>
                      <div className={styles.title}>{item.title}</div>
                      <div className={styles.subrow}>
                        <div className={styles.itemId}>{item.item_id}</div>
                        {showHistory ? (
                          <PriceSparkline data={historyMap[item.item_id] ?? []} />
                        ) : null}
                      </div>
                    </div>
                  </div>
                </td>
                <td className={styles.mono}>${item.recommended_price.toFixed(2)}</td>
                <td className={styles.mono}>
                  {item.current_market_price > 0 ? `$${item.current_market_price.toFixed(2)}` : '—'}
                </td>
                <td className={`${styles.mono} ${driftClass(item.price_drift_pct)}`}>
                  {driftLabel(item.price_drift_pct)}
                </td>
                <td className={styles.mono}>{formatTrackedDate(item.listed_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
