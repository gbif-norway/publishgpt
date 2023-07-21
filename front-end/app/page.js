'use client'

import styles from './page.module.css'
import Dataset from './components/Dataset';

const Home = () => {
  return (
    <main className={styles.main}>
      <Dataset initialDatasetId={1} />
      {/* other elements... null*/}
    </main>
  );
};

export default Home;