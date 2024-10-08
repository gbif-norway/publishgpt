import './globals.css'
import { Inter, IBM_Plex_Serif } from 'next/font/google'
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';

const inter = Inter({ subsets: ['latin'] })
const ibmPlexSerif = IBM_Plex_Serif({ subsets: ['latin'], weight: '400' });

export const metadata = {
  title: 'ChatIPT',
  description: 'Generated by create next app',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-bs-theme="dark" className="dark">
      <head>
        <title>ChatIPT</title>
      </head>
      <body className={inter.className}>
        <h1 className={`${ibmPlexSerif.className} title`}>ChatIPT</h1>
        {children}
      </body>
    </html>
  )
}
