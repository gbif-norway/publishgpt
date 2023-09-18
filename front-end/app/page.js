'use client'

import styles from './app.css'
import Dataset from './components/Dataset';

const Home = () => {
  return (
    <div className="col-lg-8 mx-auto p-4 py-md-5">
      <main>
        <Dataset initialDatasetId={20} />
      </main>
    </div>
  );
};

export default Home;
