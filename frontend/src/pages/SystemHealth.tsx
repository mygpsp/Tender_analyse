/**
 * System Health Dashboard
 * Monitors data sync status and displays update logs
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
    Chip,
    Collapse,
    IconButton,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import RefreshIcon from '@mui/icons-material/Refresh';
import {
    getUpdateLogs,
    UpdateLogsResponse,
} from '../services/systemApi';

const SystemHealth: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [logsData, setLogsData] = useState<UpdateLogsResponse | null>(null);
    const [expandedRow, setExpandedRow] = useState<string | null>(null);

    useEffect(() => {
        loadData();

        // Auto-refresh every 5 minutes
        const interval = setInterval(loadData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getUpdateLogs();
            setLogsData(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load system logs');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleString();
    };

    const formatDuration = (seconds: number) => {
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        return `${(seconds / 60).toFixed(1)}m`;
    };

    const getStatusColor = (status: string) => {
        return status === 'SUCCESS' ? 'success' : 'error';
    };

    const getStatusIcon = (status: string) => {
        return status === 'SUCCESS' ? (
            <CheckCircleIcon color="success" />
        ) : (
            <ErrorIcon color="error" />
        );
    };

    const getHealthStatus = () => {
        if (!logsData || !logsData.latest_status) {
            return { color: 'warning', text: 'No Data' };
        }

        const isRecent = logsData.last_run_age_hours !== null && logsData.last_run_age_hours < 24;
        const isSuccess = logsData.latest_status === 'SUCCESS';

        if (isSuccess && isRecent) {
            return { color: 'success', text: 'Healthy' };
        } else if (!isSuccess) {
            return { color: 'error', text: 'Failed' };
        } else {
            return { color: 'warning', text: 'Stale' };
        }
    };

    if (loading && !logsData) {
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

    const healthStatus = getHealthStatus();
    const latestLog = logsData?.logs?.[0];

    return (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4">System Health</Typography>
                <IconButton onClick={loadData} disabled={loading}>
                    <RefreshIcon />
                </IconButton>
            </Box>

            {/* Status Header */}
            <Paper sx={{ p: 3, mb: 3, bgcolor: `${healthStatus.color}.50` }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box
                        sx={{
                            width: 24,
                            height: 24,
                            borderRadius: '50%',
                            bgcolor: `${healthStatus.color}.main`,
                            animation: healthStatus.color === 'success' ? 'pulse 2s infinite' : 'none',
                            '@keyframes pulse': {
                                '0%, 100%': { opacity: 1 },
                                '50%': { opacity: 0.5 },
                            },
                        }}
                    />
                    <Typography variant="h5">
                        Data Sync Status: {healthStatus.text}
                    </Typography>
                </Box>
            </Paper>

            {/* KPI Cards */}
            {latestLog && (
                <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="text.secondary" gutterBottom>
                                    Last Run
                                </Typography>
                                <Typography variant="h4">
                                    {logsData?.last_run_age_hours !== null
                                        ? `${logsData.last_run_age_hours.toFixed(1)}h ago`
                                        : 'N/A'}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    {formatDate(latestLog.timestamp)}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>

                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="text.secondary" gutterBottom>
                                    New Tenders
                                </Typography>
                                <Typography variant="h4" color="primary.main">
                                    {latestLog.metrics.new_tenders_added}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Added in last run
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>

                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="text.secondary" gutterBottom>
                                    Updated Tenders
                                </Typography>
                                <Typography variant="h4" color="success.main">
                                    {latestLog.metrics.status_changes_detected}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Status changes detected
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>

                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6" color="text.secondary" gutterBottom>
                                    Active Re-checked
                                </Typography>
                                <Typography variant="h4" color="info.main">
                                    {latestLog.metrics.total_active_rechecked}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Tenders verified
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            )}

            {/* Logs Table */}
            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Recent Sync History
                </Typography>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell />
                                <TableCell>Time</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell align="right">New</TableCell>
                                <TableCell align="right">Updated</TableCell>
                                <TableCell align="right">Re-checked</TableCell>
                                <TableCell align="right">Duration</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {logsData?.logs.slice(0, 10).map((log) => (
                                <React.Fragment key={log.run_id}>
                                    <TableRow hover>
                                        <TableCell>
                                            <IconButton
                                                size="small"
                                                onClick={() => setExpandedRow(expandedRow === log.run_id ? null : log.run_id)}
                                            >
                                                {expandedRow === log.run_id ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                                            </IconButton>
                                        </TableCell>
                                        <TableCell>{formatDate(log.timestamp)}</TableCell>
                                        <TableCell>
                                            <Chip
                                                icon={getStatusIcon(log.status)}
                                                label={log.status}
                                                color={getStatusColor(log.status)}
                                                size="small"
                                            />
                                        </TableCell>
                                        <TableCell align="right">{log.metrics.new_tenders_added}</TableCell>
                                        <TableCell align="right">{log.metrics.status_changes_detected}</TableCell>
                                        <TableCell align="right">{log.metrics.total_active_rechecked}</TableCell>
                                        <TableCell align="right">{formatDuration(log.duration_seconds)}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
                                            <Collapse in={expandedRow === log.run_id} timeout="auto" unmountOnExit>
                                                <Box sx={{ margin: 2 }}>
                                                    <Typography variant="h6" gutterBottom component="div">
                                                        Run Details
                                                    </Typography>
                                                    <Grid container spacing={2}>
                                                        <Grid item xs={12} md={6}>
                                                            <Typography variant="body2"><strong>Run ID:</strong> {log.run_id}</Typography>
                                                            <Typography variant="body2"><strong>Data File:</strong> {log.data_file}</Typography>
                                                            <Typography variant="body2"><strong>Total Tenders:</strong> {log.metrics.total_tenders}</Typography>
                                                        </Grid>
                                                        <Grid item xs={12} md={6}>
                                                            {log.metrics.errors.length > 0 && (
                                                                <>
                                                                    <Typography variant="body2" color="error"><strong>Errors:</strong></Typography>
                                                                    {log.metrics.errors.map((err, idx) => (
                                                                        <Typography key={idx} variant="body2" color="error">
                                                                            • {err}
                                                                        </Typography>
                                                                    ))}
                                                                </>
                                                            )}
                                                        </Grid>
                                                    </Grid>
                                                </Box>
                                            </Collapse>
                                        </TableCell>
                                    </TableRow>
                                </React.Fragment>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>
        </Container>
    );
};

export default SystemHealth;
