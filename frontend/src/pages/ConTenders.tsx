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
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TablePagination,
    MenuItem,
    Select,
    FormControl,
    InputLabel,
    Stack,
    Chip,
} from '@mui/material'
import {
    Download as DownloadIcon,
    Assessment as AssessmentIcon,
    AttachMoney as AttachMoneyIcon,
    LocationOn as LocationOnIcon,
    TrendingUp as TrendingUpIcon,
} from '@mui/icons-material'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

interface ConTender {
    number: string
    buyer: string
    status: string
    published_date: string
    deadline_date?: string
    amount?: number
    final_price?: string
    winner_name?: string
    region?: string
    category?: string
    detail_url?: string
}

interface ConTenderStats {
    total_count: number
    total_amount: number
    avg_amount: number
    status_distribution: Record<string, number>
    region_distribution: Record<string, number>
    date_range: { from: string; to: string }
    regions_count: number
}

export default function ConTenders() {
    const [tenders, setTenders] = useState<ConTender[]>([])
    const [stats, setStats] = useState<ConTenderStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Pagination
    const [page, setPage] = useState(0)
    const [rowsPerPage, setRowsPerPage] = useState(20)
    const [total, setTotal] = useState(0)

    // Filters
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')
    const [status, setStatus] = useState('')
    const [region, setRegion] = useState('')
    const [search, setSearch] = useState('')

    const loadData = useCallback(async () => {
        try {
            setLoading(true)

            // Build query params
            const params = new URLSearchParams({
                page: String(page + 1),
                page_size: String(rowsPerPage),
            })
            if (dateFrom) params.append('date_from', dateFrom)
            if (dateTo) params.append('date_to', dateTo)
            if (status) params.append('status', status)
            if (region) params.append('region', region)
            if (search) params.append('search', search)

            // Fetch tenders
            const tendersResponse = await fetch(`http://localhost:8000/api/con-tenders?${params}`)
            const tendersData = await tendersResponse.json()

            setTenders(tendersData.items)
            setTotal(tendersData.total)

            // Fetch stats
            const statsParams = new URLSearchParams()
            if (dateFrom) statsParams.append('date_from', dateFrom)
            if (dateTo) statsParams.append('date_to', dateTo)
            if (status) statsParams.append('status', status)
            if (region) statsParams.append('region', region)

            const statsResponse = await fetch(`http://localhost:8000/api/con-tenders/stats?${statsParams}`)
            const statsData = await statsResponse.json()

            setStats(statsData)
            setError(null)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data')
        } finally {
            setLoading(false)
        }
    }, [page, rowsPerPage, dateFrom, dateTo, status, region, search])

    useEffect(() => {
        loadData()
    }, [loadData])

    const handleExport = async () => {
        const params = new URLSearchParams()
        if (dateFrom) params.append('date_from', dateFrom)
        if (dateTo) params.append('date_to', dateTo)
        if (status) params.append('status', status)
        if (region) params.append('region', region)

        window.open(`http://localhost:8000/api/con-tenders/export?${params}`, '_blank')
    }

    const handleExportDetailed = async () => {
        const params = new URLSearchParams()
        if (dateFrom) params.append('date_from', dateFrom)
        if (dateTo) params.append('date_to', dateTo)
        if (status) params.append('status', status)
        if (region) params.append('region', region)

        window.open(`http://localhost:8000/api/con-tenders/export-detailed?${params}`, '_blank')
    }

    const formatCurrency = (amount?: number | string) => {
        if (!amount) return 'N/A'
        const num = typeof amount === 'string' ? parseFloat(amount) : amount
        return new Intl.NumberFormat('ka-GE', {
            style: 'currency',
            currency: 'GEL',
            maximumFractionDigits: 2,
        }).format(num)
    }

    const formatNumber = (num: number) => {
        return new Intl.NumberFormat('ka-GE').format(num)
    }

    const regionChartData = stats
        ? Object.entries(stats.region_distribution).map(([name, value]) => ({
            name,
            value,
        }))
        : []

    if (loading && !stats) {
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
                    CON Tender Analysis
                </Typography>
                <Box display="flex" gap={2}>
                    <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleExport}>
                        Export Summary CSV
                    </Button>
                    <Button variant="contained" startIcon={<DownloadIcon />} onClick={handleExportDetailed}>
                        Export Detailed CSV
                    </Button>
                </Box>
            </Box>

            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            {/* Statistics Cards */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
                        <CardContent>
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                                <Box>
                                    <Typography variant="body2" sx={{ opacity: 0.9 }}>Total Tenders</Typography>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                                        {formatNumber(stats?.total_count || 0)}
                                    </Typography>
                                </Box>
                                <AssessmentIcon sx={{ fontSize: 48, opacity: 0.3 }} />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
                        <CardContent>
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                                <Box>
                                    <Typography variant="body2" sx={{ opacity: 0.9 }}>Total Amount</Typography>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                                        {formatCurrency(stats?.total_amount)}
                                    </Typography>
                                </Box>
                                <AttachMoneyIcon sx={{ fontSize: 48, opacity: 0.3 }} />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
                        <CardContent>
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                                <Box>
                                    <Typography variant="body2" sx={{ opacity: 0.9 }}>Average Amount</Typography>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                                        {formatCurrency(stats?.avg_amount)}
                                    </Typography>
                                </Box>
                                <TrendingUpIcon sx={{ fontSize: 48, opacity: 0.3 }} />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', color: 'white' }}>
                        <CardContent>
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                                <Box>
                                    <Typography variant="body2" sx={{ opacity: 0.9 }}>Regions</Typography>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                                        {formatNumber(stats?.regions_count || 0)}
                                    </Typography>
                                </Box>
                                <LocationOnIcon sx={{ fontSize: 48, opacity: 0.3 }} />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Filters */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>Filters</Typography>
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={2}>
                        <TextField
                            fullWidth
                            label="Date From"
                            type="date"
                            value={dateFrom}
                            onChange={(e) => setDateFrom(e.target.value)}
                            InputLabelProps={{ shrink: true }}
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <TextField
                            fullWidth
                            label="Date To"
                            type="date"
                            value={dateTo}
                            onChange={(e) => setDateTo(e.target.value)}
                            InputLabelProps={{ shrink: true }}
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <FormControl fullWidth>
                            <InputLabel>Status</InputLabel>
                            <Select value={status} onChange={(e) => setStatus(e.target.value)} label="Status">
                                <MenuItem value="">All</MenuItem>
                                <MenuItem value="გამარჯვებული გამოვლენილია">გამარჯვებული გამოვლენილია</MenuItem>
                                <MenuItem value="არ შედგა">არ შედგა</MenuItem>
                                <MenuItem value="გამოცხადებულია">გამოცხადებულია</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <TextField
                            fullWidth
                            label="Region"
                            value={region}
                            onChange={(e) => setRegion(e.target.value)}
                            placeholder="e.g., ზუგდიდი"
                        />
                    </Grid>
                    <Grid item xs={12} sm={12} md={4}>
                        <TextField
                            fullWidth
                            label="Search"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search by tender number..."
                        />
                    </Grid>
                </Grid>
            </Paper>

            {/* Region Distribution Chart */}
            {regionChartData.length > 0 && (
                <Card sx={{ mb: 3 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>Region Distribution</Typography>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={regionChartData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, value }) => `${name}: ${value}`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {regionChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            )}

            {/* Data Table */}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Tender Number</TableCell>
                            <TableCell>Date Bidding</TableCell>
                            <TableCell>Initial Price</TableCell>
                            <TableCell>Final Price</TableCell>
                            <TableCell>Winner</TableCell>
                            <TableCell>Region</TableCell>
                            <TableCell>Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {tenders.map((tender) => (
                            <TableRow key={tender.number}>
                                <TableCell>
                                    <a href={tender.detail_url} target="_blank" rel="noopener noreferrer">
                                        {tender.number}
                                    </a>
                                </TableCell>
                                <TableCell>{tender.published_date}</TableCell>
                                <TableCell>{formatCurrency(tender.amount)}</TableCell>
                                <TableCell>{formatCurrency(tender.final_price)}</TableCell>
                                <TableCell>{tender.winner_name || '-'}</TableCell>
                                <TableCell>
                                    {tender.region ? <Chip label={tender.region} size="small" /> : '-'}
                                </TableCell>
                                <TableCell>{tender.status}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
                <TablePagination
                    component="div"
                    count={total}
                    page={page}
                    onPageChange={(_, newPage) => setPage(newPage)}
                    rowsPerPage={rowsPerPage}
                    onRowsPerPageChange={(e) => {
                        setRowsPerPage(parseInt(e.target.value, 10))
                        setPage(0)
                    }}
                />
            </TableContainer>
        </Box>
    )
}
