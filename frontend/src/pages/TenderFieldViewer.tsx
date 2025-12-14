import { useEffect, useState, useCallback } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  CircularProgress,
  Alert,
  TextField,
  Stack,
  Chip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Paper,
  Grid,
} from '@mui/material'
// @ts-ignore - xlsx types may not be perfect
import * as XLSX from 'xlsx'
import {
  NavigateBefore as NavigateBeforeIcon,
  NavigateNext as NavigateNextIcon,
  ExpandMore as ExpandMoreIcon,
  ContentCopy as ContentCopyIcon,
  OpenInNew as OpenInNewIcon,
  Download as DownloadIcon,
} from '@mui/icons-material'
import { tendersApi } from '../services/api'
import type { TenderListResponse, TenderResponse } from '../services/api'

export default function TenderFieldViewer() {
  const [tenders, setTenders] = useState<TenderResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [jumpToNumber, setJumpToNumber] = useState('')

  const loadAllTenders = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Load all tenders with a large page size
      const allTenders: TenderResponse[] = []
      let page = 1
      let hasMore = true
      const pageSize = 100

      while (hasMore) {
        const response = await tendersApi.list({ page, page_size: pageSize })
        allTenders.push(...response.items)
        hasMore = response.page < response.pages
        page++
      }

      setTenders(allTenders)
      if (allTenders.length > 0) {
        setCurrentIndex(0)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tenders')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAllTenders()
  }, [loadAllTenders])

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleNext = () => {
    if (currentIndex < tenders.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handleJumpToNumber = () => {
    const trimmed = jumpToNumber.trim()
    if (!trimmed) return

    const index = tenders.findIndex(
      (t) => t.tender.number.toLowerCase().includes(trimmed.toLowerCase())
    )
    if (index !== -1) {
      setCurrentIndex(index)
      setJumpToNumber('')
    }
  }

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && currentIndex > 0) {
        setCurrentIndex(currentIndex - 1)
      } else if (e.key === 'ArrowRight' && currentIndex < tenders.length - 1) {
        setCurrentIndex(currentIndex + 1)
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => {
      window.removeEventListener('keydown', handleKeyPress)
    }
  }, [currentIndex, tenders.length])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return 'N/A'
    return new Date(timestamp * 1000).toLocaleString()
  }

  const handleExportToExcel = () => {
    if (tenders.length === 0) {
      alert('No tenders to export.')
      return
    }

    try {
      // Prepare data for Excel - include all fields from JSON
      const excelData = tenders.map((item, index) => {
        const tender = item.tender
        return {
          'Row Number': index + 1,
          'Tender Number': tender.number || '',
          'Tender Type': tender.tender_type || '',
          'Tender ID': tender.tender_id || '',
          'Buyer': tender.buyer || '',
          'Supplier': tender.supplier || '',
          'Status': tender.status || '',
          'Participants Count': tender.participants_count ?? '',
          'Amount (GEL)': tender.amount ?? '',
          'Published Date': tender.published_date || '',
          'Deadline Date': tender.deadline_date || '',
          'Category Code': tender.category_code || '',
          'Category': tender.category || '',
          'Detail URL': tender.detail_url || '',
          'Scraped At': tender.scraped_at
            ? new Date(tender.scraped_at * 1000).toLocaleString()
            : '',
          'Date Window From': tender.date_window?.from || '',
          'Date Window To': tender.date_window?.to || '',
          'Extraction Method': tender.extraction_method || '',
          'All Cells Content': tender.all_cells || '',
        }
      })

      // Create workbook and worksheet
      const worksheet = XLSX.utils.json_to_sheet(excelData)
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Tenders')

      // Auto-size columns
      if (excelData.length > 0) {
        const maxWidth = 50
        const colWidths = Object.keys(excelData[0]).map((key) => {
          const maxLength = Math.max(
            key.length,
            ...excelData.map((row) => String(row[key as keyof typeof row] || '').length)
          )
          return { wch: Math.min(maxLength + 2, maxWidth) }
        })
        worksheet['!cols'] = colWidths
      }

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().split('T')[0]
      const filename = `tenders_all_fields_${timestamp}.xlsx`

      // Write and download
      XLSX.writeFile(workbook, filename)
    } catch (error) {
      console.error('Error exporting to Excel:', error)
      alert('Failed to export to Excel. Please try again.')
    }
  }

  const currentTender = tenders[currentIndex]?.tender

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error">{error}</Alert>
        <Button onClick={loadAllTenders} sx={{ mt: 2 }}>
          Retry
        </Button>
      </Box>
    )
  }

  if (tenders.length === 0) {
    return (
      <Box>
        <Alert severity="info">No tenders found</Alert>
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">
          Tender Field Viewer
        </Typography>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleExportToExcel}
          color="success"
          disabled={tenders.length === 0}
        >
          Export All to Excel
        </Button>
      </Box>

      {/* Navigation Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <Button
            variant="contained"
            startIcon={<NavigateBeforeIcon />}
            onClick={handlePrevious}
            disabled={currentIndex === 0}
          >
            Previous
          </Button>

          <Typography variant="body1" sx={{ minWidth: '150px', textAlign: 'center' }}>
            Record {currentIndex + 1} of {tenders.length}
          </Typography>

          <Button
            variant="contained"
            endIcon={<NavigateNextIcon />}
            onClick={handleNext}
            disabled={currentIndex === tenders.length - 1}
          >
            Next
          </Button>

          <Divider orientation="vertical" flexItem />

          <TextField
            label="Jump to Tender Number"
            value={jumpToNumber}
            onChange={(e) => setJumpToNumber(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleJumpToNumber()
              }
            }}
            size="small"
            sx={{ minWidth: '200px' }}
          />
          <Button variant="outlined" onClick={handleJumpToNumber}>
            Jump
          </Button>
        </Stack>
      </Paper>

      {/* Current Tender Display */}
      {currentTender && (
        <Grid container spacing={2}>
          {/* Basic Information */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Basic Information
                </Typography>
                <Divider sx={{ mb: 2 }} />

                <FieldDisplay
                  label="Tender Number"
                  value={currentTender.number}
                  copyable
                />
                <FieldDisplay
                  label="Tender ID"
                  value={currentTender.tender_id || 'N/A'}
                  copyable
                />
                <FieldDisplay
                  label="Buyer"
                  value={currentTender.buyer}
                  copyable
                />
                <FieldDisplay
                  label="Supplier"
                  value={currentTender.supplier || 'N/A'}
                  copyable
                />
                <FieldDisplay
                  label="Status"
                  value={currentTender.status}
                  copyable
                />
                <FieldDisplay
                  label="Participants Count"
                  value={
                    currentTender.participants_count !== null
                      ? currentTender.participants_count.toString()
                      : 'N/A'
                  }
                />
                <FieldDisplay
                  label="Amount"
                  value={
                    currentTender.amount
                      ? `${currentTender.amount.toLocaleString('ka-GE')} GEL`
                      : 'N/A'
                  }
                  copyable
                />
                <FieldDisplay
                  label="Tender Type"
                  value={currentTender.tender_type || 'N/A'}
                />
              </CardContent>
            </Card>
          </Grid>

          {/* Dates and Category */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Dates & Category
                </Typography>
                <Divider sx={{ mb: 2 }} />

                <FieldDisplay
                  label="Published Date"
                  value={currentTender.published_date || 'N/A'}
                />
                <FieldDisplay
                  label="Deadline Date"
                  value={currentTender.deadline_date || 'N/A'}
                />
                <FieldDisplay
                  label="Category Code"
                  value={currentTender.category_code || 'N/A'}
                  copyable
                />
                <FieldDisplay
                  label="Category"
                  value={currentTender.category || 'N/A'}
                  copyable
                />
              </CardContent>
            </Card>
          </Grid>

          {/* Metadata */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Metadata
                </Typography>
                <Divider sx={{ mb: 2 }} />

                <FieldDisplay
                  label="Scraped At"
                  value={formatDate(currentTender.scraped_at)}
                />
                <FieldDisplay
                  label="Extraction Method"
                  value={currentTender.extraction_method || 'N/A'}
                />
                {currentTender.date_window && (
                  <>
                    <FieldDisplay
                      label="Date Window From"
                      value={currentTender.date_window.from}
                    />
                    <FieldDisplay
                      label="Date Window To"
                      value={currentTender.date_window.to}
                    />
                  </>
                )}
                {currentTender.detail_url && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Detail URL
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Button
                        href={currentTender.detail_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        size="small"
                        endIcon={<OpenInNewIcon />}
                      >
                        Open
                      </Button>
                      <IconButton
                        size="small"
                        onClick={() => copyToClipboard(currentTender.detail_url!)}
                      >
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* All Cells Content */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Accordion defaultExpanded={false}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="h6">
                      All Cells Content ({currentTender.all_cells.length} characters)
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ position: 'relative' }}>
                      <IconButton
                        size="small"
                        sx={{ position: 'absolute', top: 0, right: 0 }}
                        onClick={() => copyToClipboard(currentTender.all_cells)}
                      >
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                      <Typography
                        variant="body2"
                        component="pre"
                        sx={{
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          fontFamily: 'monospace',
                          fontSize: '0.875rem',
                          maxHeight: '400px',
                          overflow: 'auto',
                          p: 1,
                          bgcolor: 'grey.50',
                          borderRadius: 1,
                        }}
                      >
                        {currentTender.all_cells || 'N/A'}
                      </Typography>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}

interface FieldDisplayProps {
  label: string
  value: string
  copyable?: boolean
}

function FieldDisplay({ label, value, copyable = false }: FieldDisplayProps) {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(value)
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        {label}
      </Typography>
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="body1" sx={{ flex: 1, wordBreak: 'break-word' }}>
          {value}
        </Typography>
        {copyable && (
          <IconButton size="small" onClick={copyToClipboard}>
            <ContentCopyIcon fontSize="small" />
          </IconButton>
        )}
      </Stack>
    </Box>
  )
}

