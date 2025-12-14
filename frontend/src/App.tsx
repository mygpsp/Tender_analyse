import { Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tenders from './pages/Tenders'
import Analytics from './pages/Analytics'
import TenderSelection from './pages/TenderSelection'
import TenderFieldViewer from './pages/TenderFieldViewer'
import Suppliers from './pages/Suppliers'
import Coverage from './pages/Coverage'
import DataReview from './pages/DataReview'
import ConTenders from './pages/ConTenders'
import MarketAnalysis from './pages/MarketAnalysis'
import SystemHealth from './pages/SystemHealth'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tenders" element={<Tenders />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/selection" element={<TenderSelection />} />
          <Route path="/tender-viewer" element={<TenderFieldViewer />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/coverage" element={<Coverage />} />
          <Route path="/data-review" element={<DataReview />} />
          <Route path="/con-tenders" element={<ConTenders />} />
          <Route path="/market-analysis" element={<MarketAnalysis />} />
          <Route path="/system-health" element={<SystemHealth />} />
        </Routes>
      </Layout>
    </ThemeProvider>
  )
}

export default App

