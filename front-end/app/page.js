'use client'

import styles from './app.css'
import Dataset from './components/Dataset';

const Home = () => {
  return (
    <main>
      <Dataset initialDatasetId={2} />
    </main>
  );
};

export default Home;
