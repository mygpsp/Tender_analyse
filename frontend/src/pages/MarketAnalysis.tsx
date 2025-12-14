/**
 * Market Analysis Dashboard
 * Displays comprehensive market analysis with price trends, market share, and failure rates
 */
import React, { useState, useEffect } from 'react';
import {
    Container,
    Typography,
    Grid,
    Paper,
    Card,
    CardContent,
    Box,
    CircularProgress,
    Alert,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
} from '@mui/material';
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
} from 'recharts';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import BusinessIcon from '@mui/icons-material/Business';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import {
    getKPIs,
    getPriceTrends,
    getMarketShare,
    getFailures,
    getHotOpportunities,
    KPIs,
    PriceTrend,
    MarketShare,
    Failures,
    HotOpportunities,
} from '../services/marketAnalysisApi';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF6B9D', '#C0C0C0', '#FFD700'];

const MarketAnalysis: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [kpis, setKpis] = useState<KPIs | null>(null);
    const [priceTrends, setPriceTrends] = useState<PriceTrend | null>(null);
    const [marketShare, setMarketShare] = useState<MarketShare | null>(null);
    const [failures, setFailures] = useState<Failures | null>(null);
    const [hotOpportunities, setHotOpportunities] = useState<HotOpportunities | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Load all data in parallel
            const [kpisData, trendsData, shareData, failuresData, opportunitiesData] = await Promise.all([
                getKPIs(),
                getPriceTrends(),
                getMarketShare(),
                getFailures(),
                getHotOpportunities(),
            ]);

            setKpis(kpisData);
            setPriceTrends(trendsData);
            setMarketShare(shareData);
            setFailures(failuresData);
            setHotOpportunities(opportunitiesData);
        } catch (err: any) {
            setError(err.message || 'Failed to load market analysis data');
        } finally {
            setLoading(false);
        }
    };

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('ka-GE', {
            style: 'currency',
            currency: 'GEL',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    };

    const formatNumber = (value: number) => {
        return new Intl.NumberFormat('ka-GE').format(value);
    };

    // Prepare price evolution data for chart
    const preparePriceEvolutionData = () => {
        if (!priceTrends) return [];

        return priceTrends.years.map(year => {
            const dataPoint: any = { year };
            priceTrends.regions.slice(0, 5).forEach(region => {
                dataPoint[region] = priceTrends.data[region]?.[year.toString()] || null;
            });
            return dataPoint;
        });
    };

    // Prepare market share data for pie chart
    const prepareMarketShareData = () => {
        if (!marketShare) return [];
        return marketShare.top_winners.map(winner => ({
            name: winner.name,
            value: winner.total_value,
        }));
    };

    // Prepare failure rates data for bar chart
    const prepareFailureRatesData = () => {
        if (!failures) return [];
        return failures.regions.map(region => ({
            name: region.name,
            rate: region.failure_rate,
            failed: region.failed,
            total: region.total,
        }));
    };

    if (loading) {
        return (
            <Container maxWidth="xl" sx={{ mt: 4, mb: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                <CircularProgress size={60} />
            </Container>
        );
    }

    if (error) {
        return (
            <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
                <Alert severity="error">{error}</Alert>
            </Container>
        );
    }

    return (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h4" gutterBottom>
                Market Analysis Dashboard
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
                Comprehensive analysis of Georgian government tenders with corrected regional data
            </Typography>

            {/* KPI Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} md={4}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                <BusinessIcon sx={{ mr: 1, color: 'primary.main' }} />
                                <Typography variant="h6">Total Tenders</Typography>
                            </Box>
                            <Typography variant="h3">{kpis ? formatNumber(kpis.total_tenders) : '-'}</Typography>
                            <Typography variant="body2" color="text.secondary">Processed tenders</Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                <TrendingUpIcon sx={{ mr: 1, color: 'success.main' }} />
                                <Typography variant="h6">Avg Inflation</Typography>
                            </Box>
                            <Typography variant="h3">{kpis ? `${kpis.avg_inflation.toFixed(1)}%` : '-'}</Typography>
                            <Typography variant="body2" color="text.secondary">Price growth (2020-2025)</Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                <AttachMoneyIcon sx={{ mr: 1, color: 'warning.main' }} />
                                <Typography variant="h6">Market Volume</Typography>
                            </Box>
                            <Typography variant="h3">{kpis ? formatCurrency(kpis.total_market_volume) : '-'}</Typography>
                            <Typography variant="body2" color="text.secondary">Total contract value</Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Charts Row 1 */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                {/* Price Evolution Chart */}
                <Grid item xs={12} md={8}>
                    <Paper sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Price Evolution by Region (2020-2025)</Typography>
                        <ResponsiveContainer width="100%" height={400}>
                            <LineChart data={preparePriceEvolutionData()}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="year" />
                                <YAxis />
                                <Tooltip formatter={(value: any) => formatCurrency(value)} />
                                <Legend />
                                {priceTrends?.regions.slice(0, 5).map((region, index) => (
                                    <Line
                                        key={region}
                                        type="monotone"
                                        dataKey={region}
                                        stroke={COLORS[index % COLORS.length]}
                                        strokeWidth={2}
                                        dot={{ r: 4 }}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </Paper>
                </Grid>

                {/* Market Share Pie Chart */}
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Competitor Market Share</Typography>
                        <ResponsiveContainer width="100%" height={400}>
                            <PieChart>
                                <Pie
                                    data={prepareMarketShareData()}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={(entry) => `${entry.name.substring(0, 15)}...`}
                                    outerRadius={120}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {prepareMarketShareData().map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip formatter={(value: any) => formatCurrency(value)} />
                            </PieChart>
                        </ResponsiveContainer>
                    </Paper>
                </Grid>
            </Grid>

            {/* Charts Row 2 */}
            <Grid container spacing={3}>
                {/* Failure Rates Bar Chart */}
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Ghost Towns (Highest Failure Rates)</Typography>
                        <ResponsiveContainer width="100%" height={400}>
                            <BarChart data={prepareFailureRatesData()}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                                <YAxis label={{ value: 'Failure Rate (%)', angle: -90, position: 'insideLeft' }} />
                                <Tooltip formatter={(value: any, name: string) => {
                                    if (name === 'rate') return `${value.toFixed(1)}%`;
                                    return value;
                                }} />
                                <Bar dataKey="rate" fill="#FF8042" />
                            </BarChart>
                        </ResponsiveContainer>
                    </Paper>
                </Grid>

                {/* Hot Opportunities Table */}
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Hot Opportunities</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Regions with high failure rates (potential re-tenders)
                        </Typography>
                        <TableContainer sx={{ maxHeight: 350 }}>
                            <Table stickyHeader size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell><strong>Region</strong></TableCell>
                                        <TableCell align="right"><strong>Failed</strong></TableCell>
                                        <TableCell align="right"><strong>Total</strong></TableCell>
                                        <TableCell align="right"><strong>Rate</strong></TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {hotOpportunities?.opportunities.map((opp) => (
                                        <TableRow key={opp.name} hover>
                                            <TableCell>{opp.name}</TableCell>
                                            <TableCell align="right">{opp.failed}</TableCell>
                                            <TableCell align="right">{opp.total}</TableCell>
                                            <TableCell align="right" sx={{ color: opp.failure_rate > 40 ? 'error.main' : 'warning.main' }}>
                                                {opp.failure_rate.toFixed(1)}%
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Paper>
                </Grid>
            </Grid>
        </Container>
    );
};

export default MarketAnalysis;
