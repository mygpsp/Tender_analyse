import { useEffect, useState } from 'react'
import {
    Box,
    Typography,
    Paper,
    Grid,
    Card,
    CardContent,
    CircularProgress,
    Alert,
    TextField,
    Button,
    Stack,
    Chip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    LinearProgress,
    FormControlLabel,
    Checkbox,
    Tabs,
    Tab,
} from '@mui/material'
import {
    PieChart,
    Pie,
    Cell,
    Tooltip,
    ResponsiveContainer,
} from 'recharts'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import { coverageApi, type CoverageStats } from '../services/api'

interface TabPanelProps {
    children?: React.ReactNode
    index: number
    value: number
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`coverage-tabpanel-${index}`}
            aria-labelledby={`coverage-tab-${index}`}
            {...other}
        >
            {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
        </div>
    )
}

export default function Coverage() {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [stats, setStats] = useState<CoverageStats | null>(null)
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')
    const [filterByPublishedDate, setFilterByPublishedDate] = useState(true)
    const [filterByDeadlineDate, setFilterByDeadlineDate] = useState(true)
    const [activeTab, setActiveTab] = useState(0)

    const loadStats = async () => {
        try {
            setLoading(true)
            setError(null)

            const params: any = {}
            if (dateFrom) params.date_from = dateFrom
            if (dateTo) params.date_to = dateTo
            if (dateFrom || dateTo) {
                params.filter_by_published_date = filterByPublishedDate
                params.filter_by_deadline_date = filterByDeadlineDate
            }

            const data = await coverageApi.getStats(params)
            setStats(data)
        } catch (err) {
            console.error('Error loading coverage stats:', err)
            setError(err instanceof Error ? err.message : 'Failed to load coverage statistics')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadStats()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const handleApplyFilters = () => {
        loadStats()
    }

    const handleClearFilters = () => {
        setDateFrom('')
        setDateTo('')
        setFilterByPublishedDate(true)
        setFilterByDeadlineDate(true)
    }

    const handleSetActiveTenders = () => {
        const today = new Date().toISOString().split('T')[0]
        setDateFrom(today)
        setDateTo('')
        setFilterByPublishedDate(false)
        setFilterByDeadlineDate(true)
    }

    if (loading && !stats) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
            </Box>
        )
    }

    if (error) {
        return (
            <Box p={3}>
                <Alert severity="error">{error}</Alert>
            </Box>
        )
    }

    if (!stats) {
        return (
            <Box p={3}>
                <Alert severity="info">No coverage data available</Alert>
            </Box>
        )
    }

    const pieData = [
        { name: 'Scraped', value: stats.summary.scraped, color: '#4caf50' },
        { name: 'Not Scraped', value: stats.summary.non_scraped, color: '#f44336' },
    ]

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>
                Data Coverage Analysis
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Compare scraped vs non-scraped tender data to identify gaps and track scraping progress.
            </Typography>

            {/* Filters */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Filters
                </Typography>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={6} md={3}>
                        <TextField
                            label="Date From"
                            type="date"
                            value={dateFrom}
                            onChange={(e) => setDateFrom(e.target.value)}
                            fullWidth
                            InputLabelProps={{ shrink: true }}
                            size="small"
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <TextField
                            label="Date To"
                            type="date"
                            value={dateTo}
                            onChange={(e) => setDateTo(e.target.value)}
                            fullWidth
                            InputLabelProps={{ shrink: true }}
                            size="small"
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={filterByPublishedDate}
                                    onChange={(e) => setFilterByPublishedDate(e.target.checked)}
                                    size="small"
                                />
                            }
                            label="Filter by Published Date"
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={filterByDeadlineDate}
                                    onChange={(e) => setFilterByDeadlineDate(e.target.checked)}
                                    size="small"
                                />
                            }
                            label="Filter by Deadline Date"
                        />
                    </Grid>
                    <Grid item xs={12}>
                        <Stack direction="row" spacing={1}>
                            <Button variant="contained" onClick={handleApplyFilters} disabled={loading}>
                                Apply Filters
                            </Button>
                            <Button variant="outlined" onClick={handleClearFilters}>
                                Clear Filters
                            </Button>
                            <Button variant="outlined" onClick={handleSetActiveTenders}>
                                Show Active Tenders
                            </Button>
                        </Stack>
                    </Grid>
                </Grid>
            </Paper>

            {/* Summary Cards */}
            <Grid container spacing={3} mb={3}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card>
                        <CardContent>
                            <Typography color="text.secondary" gutterBottom>
                                Total Tenders
                            </Typography>
                            <Typography variant="h4">{stats.summary.total.toLocaleString()}</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#e8f5e9' }}>
                        <CardContent>
                            <Stack direction="row" alignItems="center" spacing={1}>
                                <CheckCircleIcon color="success" />
                                <Typography color="text.secondary" gutterBottom>
                                    Scraped
                                </Typography>
                            </Stack>
                            <Typography variant="h4" color="success.main">
                                {stats.summary.scraped.toLocaleString()}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#ffebee' }}>
                        <CardContent>
                            <Stack direction="row" alignItems="center" spacing={1}>
                                <CancelIcon color="error" />
                                <Typography color="text.secondary" gutterBottom>
                                    Not Scraped
                                </Typography>
                            </Stack>
                            <Typography variant="h4" color="error.main">
                                {stats.summary.non_scraped.toLocaleString()}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#e3f2fd' }}>
                        <CardContent>
                            <Stack direction="row" alignItems="center" spacing={1}>
                                <TrendingUpIcon color="primary" />
                                <Typography color="text.secondary" gutterBottom>
                                    Coverage
                                </Typography>
                            </Stack>
                            <Typography variant="h4" color="primary.main">
                                {stats.summary.coverage_percentage.toFixed(1)}%
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Pie Chart */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Coverage Overview
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, value, percent }) =>
                                `${name}: ${value.toLocaleString()} (${(percent * 100).toFixed(1)}%)`
                            }
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                        >
                            {pieData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip />
                    </PieChart>
                </ResponsiveContainer>
            </Paper>

            {/* Tabs for detailed breakdowns */}
            <Paper sx={{ p: 3 }}>
                <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                    <Tab label="By Date" />
                    <Tab label="By Category" />
                    <Tab label="By Buyer" />
                </Tabs>

                {/* By Date Tab */}
                <TabPanel value={activeTab} index={0}>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Date</TableCell>
                                    <TableCell align="right">Total</TableCell>
                                    <TableCell align="right">Scraped</TableCell>
                                    <TableCell align="right">Not Scraped</TableCell>
                                    <TableCell>Coverage</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {stats.by_date.map((row) => (
                                    <TableRow key={row.date}>
                                        <TableCell>{row.date}</TableCell>
                                        <TableCell align="right">{row.total}</TableCell>
                                        <TableCell align="right">
                                            <Chip
                                                label={row.scraped}
                                                size="small"
                                                color="success"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell align="right">
                                            <Chip
                                                label={row.total - row.scraped}
                                                size="small"
                                                color="error"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={row.coverage}
                                                    sx={{ flexGrow: 1, height: 8, borderRadius: 1 }}
                                                />
                                                <Typography variant="body2" sx={{ minWidth: 50 }}>
                                                    {row.coverage.toFixed(1)}%
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </TabPanel>

                {/* By Category Tab */}
                <TabPanel value={activeTab} index={1}>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Category</TableCell>
                                    <TableCell align="right">Total</TableCell>
                                    <TableCell align="right">Scraped</TableCell>
                                    <TableCell align="right">Not Scraped</TableCell>
                                    <TableCell>Coverage</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {stats.by_category.map((row, index) => (
                                    <TableRow key={index}>
                                        <TableCell>{row.category}</TableCell>
                                        <TableCell align="right">{row.total}</TableCell>
                                        <TableCell align="right">
                                            <Chip
                                                label={row.scraped}
                                                size="small"
                                                color="success"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell align="right">
                                            <Chip
                                                label={row.total - row.scraped}
                                                size="small"
                                                color="error"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={row.coverage}
                                                    sx={{ flexGrow: 1, height: 8, borderRadius: 1 }}
                                                />
                                                <Typography variant="body2" sx={{ minWidth: 50 }}>
                                                    {row.coverage.toFixed(1)}%
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </TabPanel>

                {/* By Buyer Tab */}
                <TabPanel value={activeTab} index={2}>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Buyer</TableCell>
                                    <TableCell align="right">Total</TableCell>
                                    <TableCell align="right">Scraped</TableCell>
                                    <TableCell align="right">Not Scraped</TableCell>
                                    <TableCell>Coverage</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {stats.by_buyer.map((row, index) => (
                                    <TableRow key={index}>
                                        <TableCell>{row.buyer}</TableCell>
                                        <TableCell align="right">{row.total}</TableCell>
                                        <TableCell align="right">
                                            <Chip
                                                label={row.scraped}
                                                size="small"
                                                color="success"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell align="right">
                                            <Chip
                                                label={row.total - row.scraped}
                                                size="small"
                                                color="error"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={row.coverage}
                                                    sx={{ flexGrow: 1, height: 8, borderRadius: 1 }}
                                                />
                                                <Typography variant="body2" sx={{ minWidth: 50 }}>
                                                    {row.coverage.toFixed(1)}%
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </TabPanel>
            </Paper>
        </Box>
    )
}
