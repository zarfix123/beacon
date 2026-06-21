import AskTheNetwork from './components/AskTheNetwork.jsx'
import LiveQueryDebug from './components/LiveQueryDebug.jsx'

export default function App() {
  // ?debug -> the live walking skeleton (real backend); default -> Hao's visual shell.
  const debug = typeof window !== 'undefined' && window.location.search.includes('debug')
  return debug ? <LiveQueryDebug /> : <AskTheNetwork />
}
