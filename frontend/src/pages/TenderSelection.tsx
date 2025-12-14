import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Paper,
  Button,
  Stack,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material'
import {
  Delete as DeleteIcon,
  ArrowBack as ArrowBackIcon,
  Download as DownloadIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material'
import { tendersApi } from '../services/api'
import type { TenderResponse } from '../services/api'

export default function TenderSelection() {
  const navigate = useNavigate()
  const [selectedNumbers, setSelectedNumbers] = useState<string[]>([])
  const [tenderDetails, setTenderDetails] = useState<Map<string, TenderResponse>>(new Map())
  const [loading, setLoading] = useState(true)
  const [scrapingDialogOpen, setScrapingDialogOpen] = useState(false)
  const [scrapingNumbers, setScrapingNumbers] = useState<string>('')

  useEffect(() => {
    // Load selected tender numbers from localStorage
    const saved = localStorage.getItem('selectedTenderNumbers')
    if (saved) {
      try {
        const numbers = JSON.parse(saved)
        setSelectedNumbers(numbers)
        loadTenderDetails(numbers)
      } catch (e) {
        console.error('Failed to load selected tenders', e)
        setLoading(false)
      }
    } else {
      setLoading(false)
    }
  }, [])

  const loadTenderDetails = async (tenderNumbers: string[]) => {
    if (tenderNumbers.length === 0) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      // Load details for each tender number
      // For now, we'll search for them - in future, we can have a direct lookup
      const details = new Map<string, TenderResponse>()
      
      // Search for each tender number
      for (const number of tenderNumbers) {
        try {
          const data = await tendersApi.list({
            page: 1,
            page_size: 1,
            tender_number: number,
          })
          
          if (data.items.length > 0) {
            details.set(number, data.items[0])
          }
        } catch (e) {
          console.error(`Failed to load details for ${number}`, e)
        }
      }
      
      setTenderDetails(details)
    } catch (err) {
      console.error('Failed to load tender details', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = (tenderNumber: string) => {
    const newNumbers = selectedNumbers.filter(n => n !== tenderNumber)
    setSelectedNumbers(newNumbers)
    localStorage.setItem('selectedTenderNumbers', JSON.stringify(newNumbers))
    
    const newDetails = new Map(tenderDetails)
    newDetails.delete(tenderNumber)
    setTenderDetails(newDetails)
  }

  const handleClearAll = () => {
    setSelectedNumbers([])
    setTenderDetails(new Map())
    localStorage.removeItem('selectedTenderNumbers')
  }

  const handleExport = () => {
    const data = selectedNumbers.join('\n')
    const blob = new Blob([data], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `selected_tenders_${new Date().toISOString().split('T')[0]}.txt`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const handleStartScraping = () => {
    // Open dialog to confirm and show command
    setScrapingDialogOpen(true)
    setScrapingNumbers(selectedNumbers.join(' '))
  }

  const extractTenderNumber = (text: string) => {
    const match = text.match(/([A-Z]{2,4}\d{9,})/)
    return match ? match[1] : text.substring(0, 30)
  }

  const extractBuyerName = (text: string): string => {
    if (!text) return 'N/A'
    const patterns = [
      /შემსყიდველი:\s*<strong>([^<]+)<\/strong>/,
      /შემსყიდველი:\s*([^\n]+)/,
    ]
    for (const pattern of patterns) {
      const match = text.match(pattern)
      if (match && match[1]) {
        let name = match[1].trim()
        name = name.replace(/<[^>]+>/g, '').trim()
        if (name && name.length > 0) {
          return name
        }
      }
    }
    return text.substring(0, 50) || 'N/A'
  }

  const extractCategory = (text: string): string => {
    if (!text) return 'N/A'
    const pattern = /(\d{8})-\s*([^\n]+)/
    const match = text.match(pattern)
    if (match) {
      return `${match[1]}-${match[2].trim()}`
    }
    return 'N/A'
  }

  const formatCurrency = (amount: number | null) => {
    if (!amount) return 'N/A'
    return new Intl.NumberFormat('ka-GE', {
      style: 'currency',
      currency: 'GEL',
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const extractAmount = (text: string): number | null => {
    if (!text) return null
    const patterns = [
      /(\d+(?:`\d+)*(?:\.\d+)?)\s*ლარი/,
      /ღირებულება[:\s]+(\d+(?:`\d+)*(?:\.\d+)?)/,
    ]
    for (const pattern of patterns) {
      const match = text.match(pattern)
      if (match && match[1]) {
        const cleaned = match[1].replace(/`/g, '').replace(/,/g, '')
        const amount = parseFloat(cleaned)
        if (!isNaN(amount) && amount > 0 && amount < 1_000_000_000) {
          return amount
        }
      }
    }
    return null
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1">
            Selected Tenders
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 0.5 }}>
            {selectedNumbers.length} tender{selectedNumbers.length !== 1 ? 's' : ''} selected
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/tenders')}
          >
            Back to Tenders
          </Button>
          {selectedNumbers.length > 0 && (
            <>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExport}
              >
                Export List
              </Button>
              <Button
                variant="contained"
                startIcon={<PlayArrowIcon />}
                onClick={handleStartScraping}
                color="primary"
              >
                Scrape Details
              </Button>
            </>
          )}
        </Stack>
      </Box>

      {selectedNumbers.length === 0 ? (
        <Alert severity="info">
          No tenders selected. Go to the Tenders page to select tenders for detailed scraping.
        </Alert>
      ) : (
        <>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="body1">
                <strong>{selectedNumbers.length}</strong> tenders selected
              </Typography>
              <Button
                variant="outlined"
                size="small"
                color="error"
                onClick={handleClearAll}
              >
                Clear All
              </Button>
            </Stack>
          </Paper>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Tender Number</TableCell>
                  <TableCell>Buyer</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {selectedNumbers.map((number) => {
                  const tender = tenderDetails.get(number)
                  const allCells = tender?.tender.all_cells || ''
                  const buyerName = extractBuyerName(allCells)
                  const category = extractCategory(allCells)
                  const amount = extractAmount(allCells)

                  return (
                    <TableRow key={number} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {number}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                          {buyerName}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 250 }}>
                          {category}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight="bold">
                          {formatCurrency(amount)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleRemove(number)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {/* Scraping Dialog */}
      <Dialog open={scrapingDialogOpen} onClose={() => setScrapingDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Start Detailed Scraping</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Run the detailed scraper with the following command:
          </Alert>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={`python3 detailed_scraper/detail_scraper.py ${scrapingNumbers}`}
            InputProps={{
              readOnly: true,
            }}
            sx={{
              fontFamily: 'monospace',
              '& .MuiInputBase-input': {
                fontSize: '0.875rem',
              },
            }}
          />
          <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
            Or save to file and run:
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={2}
            value={`echo "${selectedNumbers.join('\\n')}" > tender_list.txt\npython3 detailed_scraper/detail_scraper.py $(cat tender_list.txt)`}
            InputProps={{
              readOnly: true,
            }}
            sx={{
              fontFamily: 'monospace',
              mt: 1,
              '& .MuiInputBase-input': {
                fontSize: '0.875rem',
              },
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScrapingDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              // Copy to clipboard
              navigator.clipboard.writeText(`python3 detailed_scraper/detail_scraper.py ${scrapingNumbers}`)
              setScrapingDialogOpen(false)
            }}
          >
            Copy Command
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

