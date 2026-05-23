import styles from './ConfidenceBadge.module.css';

interface Props {
  confidence: number;
  signalsAgree: boolean;
  reasoning?: string;
  animDelay?: number;
}

export default function ConfidenceBadge({ confidence, signalsAgree, reasoning, animDelay = 0 }: Props) {
  const pct = Math.round(confidence * 100);

  return (
    <div>
      <div
        className={`${styles.badge} ${signalsAgree ? styles.agree : styles.disagree}`}
        style={{ animationDelay: `${animDelay}ms` }}
      >
        {signalsAgree ? (
          <svg className={styles.icon} width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M2 7l3.5 3.5L12 3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        ) : (
          <svg className={styles.icon} width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M7 2v6M7 10.5v1" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
          </svg>
        )}
        <span className={styles.pct}>{pct}%</span>
        <span className={styles.status}>{signalsAgree ? 'Signals agree' : 'Signals disagree'}</span>
      </div>
      {reasoning && <p className={styles.reasoning}>{reasoning}</p>}
    </div>
  );
}
