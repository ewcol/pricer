import styles from './TabBar.module.css';

export type Tab = 'analyze' | 'tracked';

interface Props {
  active: Tab;
  onChange: (tab: Tab) => void;
}

export default function TabBar({ active, onChange }: Props) {
  return (
    <nav className={styles.tabBar}>
      <button
        className={`${styles.tab} ${active === 'analyze' ? styles.tabActive : ''}`}
        onClick={() => onChange('analyze')}
      >
        Price &amp; List
      </button>
      <button
        className={`${styles.tab} ${active === 'tracked' ? styles.tabActive : ''}`}
        onClick={() => onChange('tracked')}
      >
        Tracked Items
      </button>
    </nav>
  );
}
