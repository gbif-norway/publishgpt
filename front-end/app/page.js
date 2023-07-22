'use client'

import styles from './page.module.css'
import Dataset from './components/Dataset';

const Home = () => {
  return (
    <div className="col-lg-8 mx-auto p-4 py-md-5">
      <main className={styles.main}>
        <Dataset initialDatasetId={null} />
        {/* other elements... null*/}
      </main>
    </div>
  );
};

export default Home;