'use client'

import styles from './app.css'
import Dataset from './components/Dataset';

const Home = () => {
  return (
    <div className="col-lg-8 mx-auto p-4 py-md-5">
      <main>
        <Dataset initialDatasetId={10} />
        {/* other elements... null*/}
      </main>
    </div>
  );
};

export default Home;