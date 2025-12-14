import { useState, useEffect } from 'react'
import {
    Container,
    Paper,
    Typography,
    Button,
    Grid,
    Chip,
    Divider,
    Card,
    CardContent,
    IconButton,
    Link,
    Alert,
    CircularProgress,
    Table,
    TableBody,
    TableCell,
    TableRow,
    Accordion,
    AccordionSummary,
    AccordionDetails,
} from '@mui/material'
import {
    NavigateBefore,
    NavigateNext,
    OpenInNew,
    ExpandMore,
} from '@mui/icons-material'
import { detailedTendersApi, DetailedTender } from '../services/api'

export default function DataReview() {
    const [currentIndex, setCurrentIndex] = useState(0)
    const [tender, setTender] = useState<DetailedTender | null>(null)
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [hasPrevious, setHasPrevious] = useState(false)
    const [hasNext, setHasNext] = useState(false)

    const loadTender = async (offset: number) => {
        setLoading(true)
        setError(null)
        try {
            const response = await detailedTendersApi.browse({ offset, limit: 1 })
            if (response.items.length > 0) {
                setTender(response.items[0])
                setTotal(response.total)
                setCurrentIndex(offset)
                setHasPrevious(response.has_previous)
                setHasNext(response.has_next)
            } else {
                setError('No tenders found')
            }
        } catch (err) {
            console.error('Failed to load tender:', err)
            setError(err instanceof Error ? err.message : 'Failed to load tender')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadTender(0)
    }, [])

    const handlePrevious = () => {
        if (hasPrevious) {
            loadTender(currentIndex - 1)
        }
    }

    const handleNext = () => {
        if (hasNext) {
            loadTender(currentIndex + 1)
        }
    }

    const getTenderNumber = () => {
        return tender?.tender_number || tender?.procurement_number || tender?.number || 'N/A'
    }

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return 'N/A'
        try {
            return new Date(dateStr).toLocaleDateString('ka-GE')
        } catch {
            return dateStr
        }
    }

    const formatAmount = (amount?: string | number) => {
        if (!amount) return 'N/A'
        const num = typeof amount === 'string' ? parseFloat(amount) : amount
        return `${num.toLocaleString()} GEL`
    }

    if (loading && !tender) {
        return (
            <Container maxWidth="xl" sx={{ mt: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
                <CircularProgress />
            </Container>
        )
    }

    if (error && !tender) {
        return (
            <Container maxWidth="xl" sx={{ mt: 4 }}>
                <Alert severity="error">{error}</Alert>
            </Container>
        )
    }

    if (!tender) {
        return (
            <Container maxWidth="xl" sx={{ mt: 4 }}>
                <Alert severity="info">No tenders available</Alert>
            </Container>
        )
    }

    return (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
            {/* Header with Navigation */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Grid container alignItems="center" spacing={2}>
                    <Grid item>
                        <IconButton onClick={handlePrevious} disabled={!hasPrevious || loading}>
                            <NavigateBefore />
                        </IconButton>
                    </Grid>
                    <Grid item xs>
                        <Typography variant="h5" component="h1">
                            Data Review: {getTenderNumber()}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Tender {currentIndex + 1} of {total}
                        </Typography>
                    </Grid>
                    <Grid item>
                        {tender.detail_url && (
                            <Button
                                variant="contained"
                                color="primary"
                                startIcon={<OpenInNew />}
                                href={tender.detail_url}
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                Open Online
                            </Button>
                        )}
                    </Grid>
                    <Grid item>
                        <IconButton onClick={handleNext} disabled={!hasNext || loading}>
                            <NavigateNext />
                        </IconButton>
                    </Grid>
                </Grid>
            </Paper>

            {/* Basic Information */}
            <Card sx={{ mb: 2 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Basic Information
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="body2" color="text.secondary">Tender Number</Typography>
                            <Typography variant="body1" fontWeight="medium">{getTenderNumber()}</Typography>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Typography variant="body2" color="text.secondary">Tender ID</Typography>
                            <Typography variant="body1">{tender.tender_id || 'N/A'}</Typography>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Typography variant="body2" color="text.secondary">Status</Typography>
                            <Chip label={tender.status || 'N/A'} size="small" color={tender.status?.includes('გამოცხადებულია') ? 'success' : 'default'} />
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Typography variant="body2" color="text.secondary">Type</Typography>
                            <Typography variant="body1">{tender.tender_type || 'N/A'}</Typography>
                        </Grid>
                        <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary">Title</Typography>
                            <Typography variant="body1">{tender.title || 'N/A'}</Typography>
                        </Grid>
                        <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary">Category</Typography>
                            <Typography variant="body1">{tender.category || 'N/A'}</Typography>
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {/* Buyer Information */}
            <Card sx={{ mb: 2 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Buyer Information
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                        <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary">Buyer</Typography>
                            <Typography variant="body1">{tender.buyer || 'N/A'}</Typography>
                        </Grid>
                        {tender.buyer_contacts && (
                            <>
                                <Grid item xs={12} md={4}>
                                    <Typography variant="body2" color="text.secondary">Contact Name</Typography>
                                    <Typography variant="body1">{tender.buyer_contacts.name || 'N/A'}</Typography>
                                </Grid>
                                <Grid item xs={12} md={4}>
                                    <Typography variant="body2" color="text.secondary">Phone</Typography>
                                    <Typography variant="body1">{tender.buyer_contacts.phone || 'N/A'}</Typography>
                                </Grid>
                                <Grid item xs={12} md={4}>
                                    <Typography variant="body2" color="text.secondary">Email</Typography>
                                    <Typography variant="body1">{tender.buyer_contacts.email || 'N/A'}</Typography>
                                </Grid>
                            </>
                        )}
                    </Grid>
                </CardContent>
            </Card>

            {/* Dates */}
            <Card sx={{ mb: 2 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Important Dates
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                        <Grid item xs={12} md={3}>
                            <Typography variant="body2" color="text.secondary">Published</Typography>
                            <Typography variant="body1">{formatDate(tender.published_date)}</Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                            <Typography variant="body2" color="text.secondary">Deadline</Typography>
                            <Typography variant="body1">{formatDate(tender.deadline_date)}</Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                            <Typography variant="body2" color="text.secondary">Entry Date</Typography>
                            <Typography variant="body1">{formatDate(tender.entry_date)}</Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                            <Typography variant="body2" color="text.secondary">Last Modified</Typography>
                            <Typography variant="body1">{formatDate(tender.last_modification)}</Typography>
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {/* Financial Information */}
            <Card sx={{ mb: 2 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Financial Information
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="body2" color="text.secondary">Estimated Value</Typography>
                            <Typography variant="body1" fontWeight="medium">{formatAmount(tender.estimated_value)}</Typography>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Typography variant="body2" color="text.secondary">Currency</Typography>
                            <Typography variant="body1">{tender.currency || 'GEL'}</Typography>
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {/* Documents */}
            {tender.documents && tender.documents.length > 0 && (
                <Card sx={{ mb: 2 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Documents ({tender.documents.length})
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Table size="small">
                            <TableBody>
                                {tender.documents.map((doc, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell>{doc.name || `Document ${idx + 1}`}</TableCell>
                                        <TableCell>{doc.type || 'unknown'}</TableCell>
                                        <TableCell align="right">
                                            {doc.url && (
                                                <Link href={doc.url} target="_blank" rel="noopener noreferrer">
                                                    <OpenInNew fontSize="small" />
                                                </Link>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            )}

            {/* Tabs Data */}
            {tender.tabs_data && Object.keys(tender.tabs_data).length > 0 && (
                <Card sx={{ mb: 2 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Tabs Data
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        {Object.entries(tender.tabs_data).map(([tabName, tabData]: [string, any]) => (
                            <Accordion key={tabName}>
                                <AccordionSummary expandIcon={<ExpandMore />}>
                                    <Typography>{tabName}</Typography>
                                </AccordionSummary>
                                <AccordionDetails>
                                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                                        {tabData.text || 'No text content'}
                                    </Typography>
                                </AccordionDetails>
                            </Accordion>
                        ))}
                    </CardContent>
                </Card>
            )}

            {/* Description */}
            {tender.description && (
                <Card sx={{ mb: 2 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Description
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {tender.description}
                        </Typography>
                    </CardContent>
                </Card>
            )}

            {/* Additional Information */}
            {tender.additional_information && (
                <Card sx={{ mb: 2 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Additional Information
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {tender.additional_information}
                        </Typography>
                    </CardContent>
                </Card>
            )}
        </Container>
    )
}
