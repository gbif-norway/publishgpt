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
      <Dataset initialDatasetId={7} />

      <div className="modal modal-lg fade" id="myModal" tabIndex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true">
        <div className="modal-dialog">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="exampleModalLabel">Welcome to ChatIPT</h5>
              <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div className="modal-body">
              <div className="alert alert-warning" role="alert">
              <p>ChatIPT is a data publication chatbot for students and researchers who are new to data publication.</p>
              <p className="no-bottom-margin">It guides users through data preparation, from cleaning and formatting to generating basic metadata, and finally publishes the data on gbif.org.</p>
              </div>
              <hr />
              <p><strong>Why is it necessary?</strong></p>
              <p>At a conservative estimate, there are 300 - 400 PhDs and MScs in Europe alone at the moment generating biodiversity data. Publishing high quality data such as this is at scale is difficult:</p>
                <ul>
                  <li><i className="bi bi-bar-chart-steps"></i> Data standardisation is hard (requires expert domain knowledge of standards, programming knowledge, specialised software, etc)</li>
                  <li><i className="bi bi-alarm"></i> GBIF node staff time and resources are limited</li>
                  <li><i className="bi bi-person-raised-hand"></i> Training workshops teach generic techniques which users find difficult to put into practice in the real world</li>
                  <li><i className="bi bi-person-lock"></i> No open access to publishing facilities - users have to get added to IPTs manually</li>
                </ul> 
              <p>ChatIPT solves these problems: a non-technical user without data standardisation knowledge only needs a web browser to go from unformatted spreadsheet to standardised, published data on GBIF.</p>
              <hr />
              <div className="alert alert-light" role="alert">
                <p><strong>Future plans</strong></p>
                <ol>
                  <li>Restrict access with an ORCID login</li>
                  <li>Create a front page dashboard listing a logged-in user's datasets, along with some stats for each dataset from the GBIF API</li>
                  <li>Give chatbot edit access for already published or work-in-progress datasets</li>
                  <li>Currently publishing using the GBIF Norway publishing institution - this would need to be opened up to more countries. National nodes would sign up for it (agreeing that ad-hoc users can publish to a generic national institution), and publicise it at their higher education institutions. </li>
                  <li>Only works well at the moment for occurrence data - expand to sampling event, checklist and others.</li>
                  <li>Add support for frictionless data & the new data models</li>
                  <li>Test chatbot thoroughly in other languages</li>
                  <li>Build in stricter safety rails to ensure the bot is only used for legitimate data publication</li>
                  <li>Parse PDF uploads (e.g. drafts of journal papers) to create better metadata for each dataset</li>
                  <li>Use the details from the user's ORCID login to give chatbot context so it can provide more tailored help. For example, it could read biographies to discover user's area of expertise and make inferences about the data from that, automatically get current institution name + address for metadata, work out likely level of experience with data publication and tailor language accordingly, and more. The chatbot could also be more personalised and human-like, addressing the user by name, commenting on the new dataset compared to the old work done previously, etc.</li>
                  <li>Currently using OpenAI's gpt4o model - experiment with open source models to reduce costs, depending on uptake</li>
                </ol>
                <p>Note: Not suitable for publishing data from a database, or for large data sources, and there are no plans to support this. A chatbot is not the right format as it needs to be done by a technician who understands the database, and as there are far fewer databases than ad-hoc spreadsheets it is (in many ways) a different problem, which we already have a great tool for: the IPT. The IPT is less good for those new to data publication who only need to publish a small, single datase once or twice every few years.</p>
              </div>
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
