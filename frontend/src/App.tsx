import { useState } from 'react';
import TabBar from './components/TabBar';
import type { Tab } from './components/TabBar';
import AnalyzeView from './views/AnalyzeView';
import TrackedView from './views/TrackedView';
import styles from './App.module.css';

export default function App() {
  const [tab, setTab] = useState<Tab>('analyze');

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.wordmark}>
          <span className={styles.wordmarkName}>Pricer</span>
          <span className={styles.wordmarkBadge}>AI</span>
        </div>
      </header>

      <TabBar active={tab} onChange={setTab} />

      <main className={styles.main}>
        {tab === 'analyze' ? <AnalyzeView /> : <TrackedView />}
      </main>
    </div>
  );
}
