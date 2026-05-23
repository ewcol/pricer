import styles from './SkeletonPanel.module.css';

interface Props {
  variant?: 'default' | 'price';
  lines?: number;
}

export default function SkeletonPanel({ variant = 'default', lines = 2 }: Props) {
  if (variant === 'price') {
    return (
      <div className={styles.wrapper}>
        <div className={styles.labelSkeleton} />
        <div className={`${styles.panel} ${styles.panelPrice}`}>
          <div className={styles.priceLine} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.labelSkeleton} />
      <div className={styles.panel}>
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className={styles.line} style={{ animationDelay: `${i * 80}ms` }} />
        ))}
      </div>
    </div>
  );
}
