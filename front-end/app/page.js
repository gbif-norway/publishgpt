'use client'

import styles from './app.css'
import Dataset from './components/Dataset'
import { useEffect } from 'react'

const Home = () => {
  useEffect(() => {
    // Dynamically import Bootstrap JavaScript to ensure it's available
    import('bootstrap/dist/js/bootstrap.bundle.min.js').then((bootstrap) => {
      const myModal = new bootstrap.Modal(document.getElementById('myModal'));

      // Show the modal on page load
      myModal.show();

      // Clean up modal and backdrop when it is hidden
      const modalElement = document.getElementById('myModal');
      modalElement.addEventListener('hidden.bs.modal', () => {
        myModal.dispose();
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach((backdrop) => backdrop.remove());
      });
    });
  }, []);

  return (
    <main>
      <Dataset initialDatasetId={42} />

      <div className="modal fade" id="myModal" tabIndex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true">
        <div className="modal-dialog">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="exampleModalLabel">Welcome to ChatIPT</h5>
              <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div className="modal-body">
              <div className="alert alert-warning" role="alert">
              <p>ChatIPT is a data publication chatbot for students and researchers who are new to data publication.</p>
              <p>It guides users through data preparation, from cleaning and formatting to generating metadata, and finally publishes the data on gbif.org.</p>
              </div>
              <hr />
              <p><strong>Why is it necessary?</strong></p>
              <p>At a conservative estimate, there are 300 - 400 PhDs in Europe alone at the moment generating biodiversity data. Publishing high quality data such as this is at scale is difficult due to national capacity GBIF node constraints, lack of easy access to publishing facilities, etc.</p> 
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default Home
