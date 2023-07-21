import Image from 'next/image'
import styles from './page.module.css'

export default function Home() {
  return (
    <main className={styles.main}>
      <h1>Hi, I'm PublishGPT</h1>
      <div className="message initial-message">
        <p>
          I can help you publish your biodiversity data to <a href="https://gbif.org" target="_blank" rel="noreferrer">gbif.org</a>. 
          Let's start by taking a look at your .xlsx or .csv file. 
          <br />
          <small>It's better if your column headings are descriptive, so I can understand them easily.</small>
        </p>
        <div className="filedrop">Drop me your file</div>
      </div>
      <div class="chats">
        <div className="message [and either user or assistant]">
          [message content]
        </div>
        <input type="text" />
      </div>
    </main>
  )
}
