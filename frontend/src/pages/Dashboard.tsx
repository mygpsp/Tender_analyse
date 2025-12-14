import { useEffect, useState, useCallback } from 'react'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  TextField,
  Button,
  Chip,
  Paper,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Stack,
  Divider,
} from '@mui/material'
import {
  FilterList as FilterListIcon,
  Clear as ClearIcon,
  Download as DownloadIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon,
  Business as BusinessIcon,
  AttachMoney as AttachMoneyIcon,
  CalendarToday as CalendarTodayIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { analyticsApi, tendersApi } from '../services/api'
import type {
  AnalyticsSummary,
  TenderListResponse,
  BuyerStats,
  CategoryStats,
  TimelinePoint,
} from '../services/api'

interface FilterState {
  dateFrom: string
  dateTo: string
  buyer: string
  status: string
  search: string
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

export default function Dashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [recentTenders, setRecentTenders] = useState<TenderListResponse | null>(null)
  const [buyerStats, setBuyerStats] = useState<BuyerStats[]>([])
  const [categoryStats, setCategoryStats] = useState<CategoryStats[]>([])
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const navigate = useNavigate()

  const [filters, setFilters] = useState<FilterState>({
    dateFrom: '',
    dateTo: '',
    buyer: '',
    status: '',
    search: '',
  })

  const [activeFilters, setActiveFilters] = useState<string[]>([])

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const params = {
        date_from: filters.dateFrom || undefined,
        date_to: filters.dateTo || undefined,
        buyer: filters.buyer || undefined,
        status: filters.status || undefined,
        search: filters.search || undefined,
      }

      const [summaryData, tendersData, buyerData, categoryData, timelineData] =
        await Promise.all([
          analyticsApi.summary(params),
          tendersApi.list({ ...params, page: 1, page_size: 5 }),
          analyticsApi.byBuyer(params),
          analyticsApi.byCategory(params),
          analyticsApi.timeline(params),
        ])

      setSummary(summaryData)
      setRecentTenders(tendersData)
      setBuyerStats(buyerData.buyers.slice(0, 5))
      setCategoryStats(categoryData.categories.slice(0, 5))
      setTimeline(timelineData.timeline.slice(-10)) // Last 10 points
      setError(null)

      // Update active filters
      const active: string[] = []
      if (filters.dateFrom) active.push(`From: ${filters.dateFrom}`)
      if (filters.dateTo) active.push(`To: ${filters.dateTo}`)
      if (filters.buyer) active.push(`Buyer: ${filters.buyer}`)
      if (filters.status) active.push(`Status: ${filters.status}`)
      if (filters.search) active.push(`Search: ${filters.search}`)
      setActiveFilters(active)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({
      dateFrom: '',
      dateTo: '',
      buyer: '',
      status: '',
      search: '',
    })
  }

  const formatCurrency = (amount?: number) => {
    if (!amount) return 'N/A'
    return new Intl.NumberFormat('ka-GE', {
      style: 'currency',
      currency: 'GEL',
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ka-GE').format(num)
  }

  const exportData = () => {
    // Simple CSV export
    const csv = [
      ['Metric', 'Value'],
      ['Total Tenders', summary?.total_tenders || 0],
      ['Total Amount', summary?.total_amount || 0],
      ['Average Amount', summary?.avg_amount || 0],
      ['Unique Buyers', summary?.unique_buyers || 0],
    ]
      .map((row) => row.join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `tender-analysis-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  if (loading && !summary) {
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
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<FilterListIcon />}
            onClick={() => setFiltersOpen(!filtersOpen)}
          >
            Filters
          </Button>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={exportData}>
            Export
          </Button>
        </Stack>
      </Box>

      {/* Filters Panel */}
      {filtersOpen && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Filter Data</Typography>
            <IconButton size="small" onClick={clearFilters}>
              <ClearIcon />
            </IconButton>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Date From"
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Date To"
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Buyer"
                value={filters.buyer}
                onChange={(e) => handleFilterChange('buyer', e.target.value)}
                placeholder="Filter by buyer..."
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Status"
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                placeholder="Filter by status..."
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Search"
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                placeholder="Search tenders..."
              />
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Active Filters */}
      {activeFilters.length > 0 && (
        <Box mb={2}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {activeFilters.map((filter, idx) => (
              <Chip
                key={idx}
                label={filter}
                onDelete={() => {
                  // Remove specific filter
                  const parts = filter.split(':')
                  if (parts.length === 2) {
                    const key = parts[0].toLowerCase().trim()
                    if (key === 'from') handleFilterChange('dateFrom', '')
                    else if (key === 'to') handleFilterChange('dateTo', '')
                    else if (key === 'buyer') handleFilterChange('buyer', '')
                    else if (key === 'status') handleFilterChange('status', '')
                    else if (key === 'search') handleFilterChange('search', '')
                  }
                }}
                size="small"
              />
            ))}
          </Stack>
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Data Availability Info */}
      {summary?.date_range && (
        <Alert
          severity="info"
          icon={<CalendarTodayIcon />}
          sx={{ mb: 3 }}
        >
          <Typography variant="body2">
            <strong>Data Available:</strong> From {summary.date_range.from} to {summary.date_range.to}
          </Typography>
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
            }}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Total Tenders
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {formatNumber(summary?.total_tenders || 0)}
                  </Typography>
                </Box>
                <AssessmentIcon sx={{ fontSize: 48, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
              color: 'white',
            }}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Total Amount
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {formatCurrency(summary?.total_amount)}
                  </Typography>
                </Box>
                <AttachMoneyIcon sx={{ fontSize: 48, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
              color: 'white',
            }}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Average Amount
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {formatCurrency(summary?.avg_amount)}
                  </Typography>
                </Box>
                <TrendingUpIcon sx={{ fontSize: 48, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
              color: 'white',
            }}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Unique Buyers
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {formatNumber(summary?.unique_buyers || 0)}
                  </Typography>
                </Box>
                <BusinessIcon sx={{ fontSize: 48, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Timeline Chart */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Tender Timeline
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" />
                  <YAxis 
                    yAxisId="right" 
                    orientation="right"
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <Tooltip
                    formatter={(value: any, name: string) => {
                      if (name === 'Total Amount') {
                        return formatCurrency(value)
                      }
                      return value
                    }}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="count"
                    stroke="#667eea"
                    strokeWidth={2}
                    name="Tender Count"
                  />
                  {timeline.some((t) => t.total_amount) && (
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="total_amount"
                      stroke="#f5576c"
                      strokeWidth={2}
                      name="Total Amount"
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Top Categories Pie Chart */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Top Categories
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={categoryStats}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ category, tender_count }) =>
                      `${category.substring(0, 15)}: ${tender_count}`
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="tender_count"
                  >
                    {categoryStats.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Top Buyers and Recent Tenders */}
      <Grid container spacing={3}>
        {/* Top Buyers */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Top Buyers
              </Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={buyerStats} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis
                    dataKey="name"
                    type="category"
                    width={150}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip />
                  <Bar dataKey="tender_count" fill="#667eea" name="Tender Count" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Tenders */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Recent Tenders</Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/tenders')}
                  sx={{ textTransform: 'none' }}
                >
                  View All
                </Button>
              </Box>
              {recentTenders?.items.length ? (
                <Stack spacing={1}>
                  {recentTenders.items.map((item) => (
                    <Paper
                      key={item.id}
                      sx={{
                        p: 2,
                        cursor: 'pointer',
                        '&:hover': { backgroundColor: '#f5f5f5' },
                      }}
                      onClick={() => navigate(`/tenders`)}
                    >
                      <Typography variant="subtitle2" fontWeight="bold">
                        {item.tender.number?.substring(0, 30) || `Tender #${item.id}`}
                      </Typography>
                      <Typography variant="body2" color="textSecondary" noWrap>
                        {item.tender.buyer || 'N/A'}
                      </Typography>
                    </Paper>
                  ))}
                </Stack>
              ) : (
                <Typography color="textSecondary">No tenders found</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
