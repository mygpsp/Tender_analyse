import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material'
import {
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
  LineChart,
  Line,
} from 'recharts'
import { analyticsApi } from '../services/api'
import type { BuyerStats, WinnerStats, CategoryStats, TimelinePoint } from '../services/api'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

export default function Analytics() {
  const navigate = useNavigate()
  const [buyerStats, setBuyerStats] = useState<BuyerStats[]>([])
  const [allWinnerStats, setAllWinnerStats] = useState<WinnerStats[]>([])
  const [winnerStats, setWinnerStats] = useState<WinnerStats[]>([])
  const [allCategoryStats, setAllCategoryStats] = useState<CategoryStats[]>([])
  const [categoryStats, setCategoryStats] = useState<CategoryStats[]>([])
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [categoryView, setCategoryView] = useState<'count' | 'amount'>('count')
  const [winnerView, setWinnerView] = useState<'count' | 'amount'>('count')

  const handleBuyerClick = (buyerName: string) => {
    navigate(`/tenders?buyer=${encodeURIComponent(buyerName)}`)
  }

  const handleWinnerClick = (winnerName: string) => {
    navigate(`/tenders?search=${encodeURIComponent(winnerName)}`)
  }

  const handleCategoryClick = (category: string) => {
    // Use full category text for better matching
    // The backend search does full-text search, so it will find tenders containing this category
    navigate(`/tenders?search=${encodeURIComponent(category)}`)
  }

  const handleTimelineClick = (date: string) => {
    // Dates are now normalized to YYYY-MM-DD format from backend
    // But handle both formats for safety
    let convertedDate = date
    if (date.includes('.')) {
      // Convert DD.MM.YYYY to YYYY-MM-DD format
      const parts = date.split('.')
      if (parts.length === 3) {
        convertedDate = `${parts[2]}-${parts[1]}-${parts[0]}`
      }
    }
    navigate(`/tenders?date_from=${convertedDate}&date_to=${convertedDate}`)
  }

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        setLoading(true)
        const [buyerData, winnerData, categoryData, timelineData] = await Promise.all([
          analyticsApi.byBuyer(),
          analyticsApi.byWinner(),
          analyticsApi.byCategory(),
          analyticsApi.timeline(),
        ])
        setBuyerStats(buyerData.buyers.slice(0, 10)) // Top 10
        setAllWinnerStats(winnerData.winners) // Store all winners
        setAllCategoryStats(categoryData.categories) // Store all categories
        // Ensure timeline is sorted by date (backend should already do this, but just in case)
        const sortedTimeline = [...timelineData.timeline].sort((a, b) => 
          a.date.localeCompare(b.date)
        )
        setTimeline(sortedTimeline)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics')
      } finally {
        setLoading(false)
      }
    }

    loadAnalytics()
  }, [])

  // Update category stats when view changes
  useEffect(() => {
    if (allCategoryStats.length > 0) {
      const sorted =
        categoryView === 'count'
          ? [...allCategoryStats].sort(
              (a, b) => (b.tender_count || 0) - (a.tender_count || 0)
            )
          : [...allCategoryStats]
              .filter((c) => c.total_amount)
              .sort((a, b) => (b.total_amount || 0) - (a.total_amount || 0))
      setCategoryStats(sorted.slice(0, 10))
    }
  }, [categoryView, allCategoryStats])

  // Update winner stats when view changes
  useEffect(() => {
    if (allWinnerStats.length > 0) {
      const sorted =
        winnerView === 'count'
          ? [...allWinnerStats].sort(
              (a, b) => (b.tender_count || 0) - (a.tender_count || 0)
            )
          : [...allWinnerStats]
              .filter((w) => w.total_amount)
              .sort((a, b) => (b.total_amount || 0) - (a.total_amount || 0))
      setWinnerStats(sorted.slice(0, 10))
    }
  }, [winnerView, allWinnerStats])

  // Update winner stats when view changes
  useEffect(() => {
    if (allWinnerStats.length > 0) {
      const sorted =
        winnerView === 'count'
          ? [...allWinnerStats].sort(
              (a, b) => (b.tender_count || 0) - (a.tender_count || 0)
            )
          : [...allWinnerStats]
              .filter((w) => w.total_amount)
              .sort((a, b) => (b.total_amount || 0) - (a.total_amount || 0))
      setWinnerStats(sorted.slice(0, 10))
    }
  }, [winnerView, allWinnerStats])

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  const formatCurrency = (amount?: number) => {
    if (!amount) return 'N/A'
    return new Intl.NumberFormat('ka-GE', {
      style: 'currency',
      currency: 'GEL',
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Analytics
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card sx={{ position: 'relative', zIndex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Tenders by Buyer (Top 10)
              </Typography>
              <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                Click on a bar to view tenders from that buyer
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart
                  data={buyerStats}
                  onClick={(data) => {
                    if (data && data.activePayload && data.activePayload[0]) {
                      const buyerName = data.activePayload[0].payload.name
                      handleBuyerClick(buyerName)
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    angle={-45}
                    textAnchor="end"
                    height={100}
                    interval={0}
                  />
                  <YAxis />
                  <Tooltip wrapperStyle={{ zIndex: 1000 }} />
                  <Legend />
                  <Bar
                    dataKey="tender_count"
                    fill="#8884d8"
                    name="Tender Count"
                    onClick={(data) => {
                      if (data && data.payload) {
                        handleBuyerClick(data.payload.name)
                      }
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Top Winners Section */}
        <Grid item xs={12} md={6}>
          <Card sx={{ position: 'relative', zIndex: 1 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6" component="h2">
                  Top Winners {winnerView === 'count' ? 'by Quantity' : 'by Amount'} (Top 10)
                </Typography>
                <ToggleButtonGroup
                  value={winnerView}
                  exclusive
                  onChange={(_, newView) => {
                    if (newView !== null) setWinnerView(newView)
                  }}
                  size="small"
                >
                  <ToggleButton value="count">Quantity</ToggleButton>
                  <ToggleButton value="amount">Amount</ToggleButton>
                </ToggleButtonGroup>
              </Stack>
              <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                Click on a bar to view tenders won by this company
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                {winnerView === 'count' ? (
                  <BarChart
                    data={winnerStats}
                    layout="vertical"
                    onClick={(data) => {
                      if (data && data.activePayload && data.activePayload[0]) {
                        const winner = data.activePayload[0].payload.name
                        handleWinnerClick(winner)
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={200}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      formatter={(value: number) => `${value} tenders`}
                      wrapperStyle={{ zIndex: 1000 }}
                    />
                    <Legend />
                    <Bar
                      dataKey="tender_count"
                      fill="#FF8042"
                      name="Tenders Won"
                      onClick={(data) => {
                        if (data && data.payload) {
                          handleWinnerClick(data.payload.name)
                        }
                      }}
                    />
                  </BarChart>
                ) : (
                  <BarChart
                    data={winnerStats.filter(w => w.total_amount)}
                    layout="vertical"
                    onClick={(data) => {
                      if (data && data.activePayload && data.activePayload[0]) {
                        const winner = data.activePayload[0].payload.name
                        handleWinnerClick(winner)
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={200}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      wrapperStyle={{ zIndex: 1000 }}
                    />
                    <Legend />
                    <Bar
                      dataKey="total_amount"
                      fill="#00C49F"
                      name="Total Amount Won"
                      onClick={(data) => {
                        if (data && data.payload) {
                          handleWinnerClick(data.payload.name)
                        }
                      }}
                    />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Winners Table */}
        <Grid item xs={12} md={6}>
          <Card sx={{ position: 'relative', zIndex: 1 }}>
            <CardContent>
              <Typography variant="h6" component="h2" gutterBottom>
                Winners Statistics
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Company</strong></TableCell>
                      <TableCell align="right"><strong>Tenders</strong></TableCell>
                      <TableCell align="right"><strong>Total Amount</strong></TableCell>
                      <TableCell align="right"><strong>Avg Amount</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {winnerStats.map((winner, index) => (
                      <TableRow
                        key={index}
                        hover
                        onClick={() => handleWinnerClick(winner.name)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{winner.name}</TableCell>
                        <TableCell align="right">{winner.tender_count}</TableCell>
                        <TableCell align="right">
                          {winner.total_amount ? formatCurrency(winner.total_amount) : 'N/A'}
                        </TableCell>
                        <TableCell align="right">
                          {winner.avg_amount ? formatCurrency(winner.avg_amount) : 'N/A'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ position: 'relative', zIndex: 1 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="h6">
                  Categories {categoryView === 'count' ? 'by Count' : 'by Amount'} (Top 10)
                </Typography>
                <ToggleButtonGroup
                  value={categoryView}
                  exclusive
                  onChange={(_, newView) => {
                    if (newView !== null) setCategoryView(newView)
                  }}
                  size="small"
                >
                  <ToggleButton value="count">Count</ToggleButton>
                  <ToggleButton value="amount">Amount</ToggleButton>
                </ToggleButtonGroup>
              </Stack>
              <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                Click on a segment/bar to view tenders in that category
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                {categoryView === 'count' ? (
                  <PieChart
                    onClick={(data) => {
                      if (data && data.activePayload && data.activePayload[0]) {
                        const category = data.activePayload[0].payload.category
                        handleCategoryClick(category)
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <Pie
                      data={categoryStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ category, tender_count, total_amount }) => {
                        const categoryShort = category.substring(0, 15)
                        const amountStr = total_amount
                          ? ` (${formatCurrency(total_amount)})`
                          : ''
                        return `${categoryShort}: ${tender_count}${amountStr}`
                      }}
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="tender_count"
                      onClick={(data) => {
                        if (data && data.payload) {
                          handleCategoryClick(data.payload.category)
                        }
                      }}
                    >
                      {categoryStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip wrapperStyle={{ zIndex: 1000 }} />
                  </PieChart>
                ) : (
                  <BarChart
                    data={categoryStats}
                    layout="vertical"
                    onClick={(data) => {
                      if (data && data.activePayload && data.activePayload[0]) {
                        const category = data.activePayload[0].payload.category
                        handleCategoryClick(category)
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis
                      dataKey="category"
                      type="category"
                      width={200}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      wrapperStyle={{ zIndex: 1000 }}
                    />
                    <Legend />
                    <Bar
                      dataKey="total_amount"
                      fill="#00C49F"
                      name="Total Amount"
                      onClick={(data) => {
                        if (data && data.payload) {
                          handleCategoryClick(data.payload.category)
                        }
                      }}
                    />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Categories Comparison Table */}
        <Grid item xs={12} md={6}>
          <Card sx={{ position: 'relative', zIndex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Category Comparison (Top 10)
              </Typography>
              <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                Click on a row to view tenders in that category
              </Typography>
              <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Category</TableCell>
                      <TableCell align="right">Count</TableCell>
                      <TableCell align="right">Total Amount</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {categoryStats.slice(0, 10).map((cat, idx) => (
                      <TableRow
                        key={idx}
                        hover
                        onClick={() => handleCategoryClick(cat.category)}
                        sx={{
                          cursor: 'pointer',
                          '&:last-child td, &:last-child th': { border: 0 },
                          '&:hover': { backgroundColor: '#f5f5f5' },
                        }}
                      >
                        <TableCell component="th" scope="row" sx={{ maxWidth: 200 }}>
                          <Typography variant="body2" noWrap>
                            {cat.category}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{cat.tender_count}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                          {formatCurrency(cat.total_amount)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card sx={{ position: 'relative', zIndex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Timeline
              </Typography>
              <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                Click on a point to view tenders from that date
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart
                  data={timeline}
                  onClick={(data) => {
                    if (data && data.activePayload && data.activePayload[0]) {
                      const date = data.activePayload[0].payload.date
                      handleTimelineClick(date)
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    tickFormatter={(value) => {
                      // Format YYYY-MM-DD to DD.MM.YYYY for display
                      if (value && value.includes('-')) {
                        const parts = value.split('-')
                        if (parts.length === 3) {
                          return `${parts[2]}.${parts[1]}.${parts[0]}`
                        }
                      }
                      return value
                    }}
                  />
                  <YAxis yAxisId="left" />
                  <YAxis 
                    yAxisId="right" 
                    orientation="right"
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <Tooltip 
                    wrapperStyle={{ zIndex: 1000 }}
                    labelFormatter={(label) => {
                      // Format YYYY-MM-DD to DD.MM.YYYY for display
                      if (label && typeof label === 'string' && label.includes('-')) {
                        const parts = label.split('-')
                        if (parts.length === 3) {
                          return `Date: ${parts[2]}.${parts[1]}.${parts[0]}`
                        }
                      }
                      return `Date: ${label}`
                    }}
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
                    stroke="#8884d8"
                    name="Tender Count"
                    onClick={(data) => {
                      if (data && data.payload) {
                        handleTimelineClick(data.payload.date)
                      }
                    }}
                  />
                  {timeline.some((t) => t.total_amount) && (
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="total_amount"
                      stroke="#00C49F"
                      name="Total Amount"
                      onClick={(data) => {
                        if (data && data.payload) {
                          handleTimelineClick(data.payload.date)
                        }
                      }}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

