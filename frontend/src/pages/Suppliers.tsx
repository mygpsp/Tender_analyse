import React, { useState, useEffect } from 'react'
import {
    Box,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TablePagination,
    TextField,
    Typography,
    Chip,
    CircularProgress,
    Alert,
    InputAdornment,
    IconButton,
    Card,
    CardContent,
    Grid,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    TableSortLabel,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import ClearIcon from '@mui/icons-material/Clear'
import BusinessIcon from '@mui/icons-material/Business'
import LocationOnIcon from '@mui/icons-material/LocationOn'
import EmailIcon from '@mui/icons-material/Email'
import PhoneIcon from '@mui/icons-material/Phone'
import LanguageIcon from '@mui/icons-material/Language'
import FilterListIcon from '@mui/icons-material/FilterList'
import CloseIcon from '@mui/icons-material/Close'

interface ContactPerson {
    full_name: string | null
    position: string | null
    telephone: string | null
    email: string | null
}

interface SupplierInfo {
    name: string | null
    identification_code: string | null
    country: string | null
    city_or_region: string | null
    legal_address: string | null
    telephone: string | null
    fax: string | null
    email: string | null
    website: string | null
}

interface Supplier {
    supplier: SupplierInfo
    contact_persons: ContactPerson[]
    cpv_codes: any[]
    registration_date: string | null
    supplier_or_buyer_type: string | null
    scraped_at: string | null
    scraping_status: string
}

interface SupplierResponse {
    id: number
    supplier: Supplier
}

interface SuppliersListResponse {
    items: SupplierResponse[]
    total: number
    page: number
    page_size: number
    pages: number
}

interface SupplierStats {
    total_suppliers: number
    by_country: Record<string, number>
    by_city: Record<string, number>
    by_type: Record<string, number>
}

const API_BASE_URL = 'http://localhost:8000'

type SortField = 'date' | 'name' | 'id'
type SortOrder = 'asc' | 'desc'

const Suppliers: React.FC = () => {
    const [suppliers, setSuppliers] = useState<SupplierResponse[]>([])
    const [stats, setStats] = useState<SupplierStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [page, setPage] = useState(0)
    const [rowsPerPage, setRowsPerPage] = useState(15)
    const [totalSuppliers, setTotalSuppliers] = useState(0)

    // Search state
    const [searchTerm, setSearchTerm] = useState('')
    const [searchInput, setSearchInput] = useState('')

    // Filter state
    const [selectedCountry, setSelectedCountry] = useState('')
    const [selectedCity, setSelectedCity] = useState('')
    const [selectedType, setSelectedType] = useState('')

    // Sort state
    const [sortBy, setSortBy] = useState<SortField>('date')
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

    // Dialog state
    const [selectedSupplier, setSelectedSupplier] = useState<SupplierResponse | null>(null)
    const [dialogOpen, setDialogOpen] = useState(false)

    // Fetch suppliers
    const fetchSuppliers = async () => {
        setLoading(true)
        setError(null)

        try {
            const params = new URLSearchParams({
                page: (page + 1).toString(),
                page_size: rowsPerPage.toString(),
                sort_by: sortBy,
                sort_order: sortOrder
            })

            if (searchTerm) params.append('search', searchTerm)
            if (selectedCountry) params.append('country', selectedCountry)
            if (selectedCity) params.append('city', selectedCity)
            if (selectedType) params.append('supplier_type', selectedType)

            const response = await fetch(`${API_BASE_URL}/api/suppliers?${params}`)

            if (!response.ok) {
                throw new Error('Failed to fetch suppliers')
            }

            const data: SuppliersListResponse = await response.json()
            setSuppliers(data.items)
            setTotalSuppliers(data.total)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred')
        } finally {
            setLoading(false)
        }
    }

    // Fetch stats
    const fetchStats = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/suppliers/stats/summary`)
            if (response.ok) {
                const data = await response.json()
                setStats(data)
            }
        } catch (err) {
            console.error('Failed to fetch stats:', err)
        }
    }

    useEffect(() => {
        fetchSuppliers()
    }, [page, rowsPerPage, searchTerm, selectedCountry, selectedCity, selectedType, sortBy, sortOrder])

    useEffect(() => {
        fetchStats()
    }, [])

    const handleChangePage = (_event: unknown, newPage: number) => {
        setPage(newPage)
    }

    const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
        setRowsPerPage(parseInt(event.target.value, 10))
        setPage(0)
    }

    const handleSearch = () => {
        setSearchTerm(searchInput)
        setPage(0)
    }

    const handleClearSearch = () => {
        setSearchInput('')
        setSearchTerm('')
        setPage(0)
    }

    const handleKeyPress = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter') {
            handleSearch()
        }
    }

    const handleSort = (field: SortField) => {
        const isAsc = sortBy === field && sortOrder === 'asc'
        // If changing field, default to desc for date and id, asc for name
        if (sortBy !== field) {
            setSortOrder(field === 'name' ? 'asc' : 'desc')
        } else {
            setSortOrder(isAsc ? 'desc' : 'asc')
        }
        setSortBy(field)
        setPage(0)
    }

    const clearFilters = () => {
        setSelectedCountry('')
        setSelectedCity('')
        setSelectedType('')
        setPage(0)
    }

    const handleRowClick = (supplier: SupplierResponse) => {
        setSelectedSupplier(supplier)
        setDialogOpen(true)
    }

    const handleCloseDialog = () => {
        setDialogOpen(false)
        setSelectedSupplier(null)
    }

    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                Suppliers
            </Typography>

            {/* Stats Cards */}
            {stats && (
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="textSecondary" gutterBottom>
                                    Total Suppliers
                                </Typography>
                                <Typography variant="h4">
                                    {stats.total_suppliers.toLocaleString()}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="textSecondary" gutterBottom>
                                    Countries
                                </Typography>
                                <Typography variant="h4">
                                    {Object.keys(stats.by_country).length}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="textSecondary" gutterBottom>
                                    Cities
                                </Typography>
                                <Typography variant="h4">
                                    {Object.keys(stats.by_city).length}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="textSecondary" gutterBottom>
                                    Supplier Types
                                </Typography>
                                <Typography variant="h4">
                                    {Object.keys(stats.by_type).length}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            )}

            {/* Filters & Search */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} md={4}>
                        <TextField
                            fullWidth
                            placeholder="Search by name, ID, or email..."
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            size="small"
                            InputProps={{
                                startAdornment: (
                                    <InputAdornment position="start">
                                        <SearchIcon />
                                    </InputAdornment>
                                ),
                                endAdornment: searchInput && (
                                    <InputAdornment position="end">
                                        <IconButton onClick={handleClearSearch} size="small">
                                            <ClearIcon />
                                        </IconButton>
                                    </InputAdornment>
                                ),
                            }}
                        />
                    </Grid>

                    <Grid item xs={12} md={2}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Country</InputLabel>
                            <Select
                                value={selectedCountry}
                                label="Country"
                                onChange={(e) => {
                                    setSelectedCountry(e.target.value)
                                    setPage(0)
                                }}
                            >
                                <MenuItem value=""><em>All</em></MenuItem>
                                {stats && Object.keys(stats.by_country).map((country) => (
                                    <MenuItem key={country} value={country}>
                                        {country} ({stats.by_country[country]})
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>

                    <Grid item xs={12} md={2}>
                        <FormControl fullWidth size="small">
                            <InputLabel>City</InputLabel>
                            <Select
                                value={selectedCity}
                                label="City"
                                onChange={(e) => {
                                    setSelectedCity(e.target.value)
                                    setPage(0)
                                }}
                            >
                                <MenuItem value=""><em>All</em></MenuItem>
                                {stats && Object.keys(stats.by_city).map((city) => (
                                    <MenuItem key={city} value={city}>
                                        {city} ({stats.by_city[city]})
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>

                    <Grid item xs={12} md={2}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Type</InputLabel>
                            <Select
                                value={selectedType}
                                label="Type"
                                onChange={(e) => {
                                    setSelectedType(e.target.value)
                                    setPage(0)
                                }}
                            >
                                <MenuItem value=""><em>All</em></MenuItem>
                                {stats && Object.keys(stats.by_type).map((type) => (
                                    <MenuItem key={type} value={type}>
                                        {type} ({stats.by_type[type]})
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>

                    <Grid item xs={12} md={2}>
                        <Button
                            variant="outlined"
                            startIcon={<FilterListIcon />}
                            onClick={clearFilters}
                            fullWidth
                            disabled={!selectedCountry && !selectedCity && !selectedType}
                        >
                            Clear Filters
                        </Button>
                    </Grid>
                </Grid>
            </Paper>

            {/* Error Alert */}
            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            {/* Suppliers Table */}
            <Paper>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', px: 2, borderBottom: '1px solid rgba(224, 224, 224, 1)' }}>
                    <Typography variant="body2" color="textSecondary" sx={{ mr: 2 }}>
                        Page {page + 1} of {Math.ceil(totalSuppliers / rowsPerPage)}
                    </Typography>
                    <TablePagination
                        rowsPerPageOptions={[10, 15, 20, 50, 100]}
                        component="div"
                        count={totalSuppliers}
                        rowsPerPage={rowsPerPage}
                        page={page}
                        onPageChange={handleChangePage}
                        onRowsPerPageChange={handleChangeRowsPerPage}
                        showFirstButton
                        showLastButton
                        sx={{ border: 'none' }}
                    />
                </Box>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>
                                    <TableSortLabel
                                        active={sortBy === 'name'}
                                        direction={sortBy === 'name' ? sortOrder : 'asc'}
                                        onClick={() => handleSort('name')}
                                    >
                                        <strong>Name</strong>
                                    </TableSortLabel>
                                </TableCell>
                                <TableCell>
                                    <TableSortLabel
                                        active={sortBy === 'id'}
                                        direction={sortBy === 'id' ? sortOrder : 'asc'}
                                        onClick={() => handleSort('id')}
                                    >
                                        <strong>ID</strong>
                                    </TableSortLabel>
                                </TableCell>
                                <TableCell><strong>Country</strong></TableCell>
                                <TableCell><strong>City</strong></TableCell>
                                <TableCell><strong>Contact</strong></TableCell>
                                <TableCell><strong>Type</strong></TableCell>
                                <TableCell>
                                    <TableSortLabel
                                        active={sortBy === 'date'}
                                        direction={sortBy === 'date' ? sortOrder : 'asc'}
                                        onClick={() => handleSort('date')}
                                    >
                                        <strong>Registered</strong>
                                    </TableSortLabel>
                                </TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {loading ? (
                                <TableRow>
                                    <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                                        <CircularProgress />
                                    </TableCell>
                                </TableRow>
                            ) : suppliers.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                                        <Typography color="textSecondary">
                                            No suppliers found
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                suppliers.map((item) => {
                                    const supplier = item.supplier.supplier
                                    return (
                                        <TableRow
                                            key={item.id}
                                            hover
                                            onClick={() => handleRowClick(item)}
                                            sx={{ cursor: 'pointer' }}
                                        >
                                            <TableCell>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    <BusinessIcon fontSize="small" color="action" />
                                                    <Typography variant="body2">
                                                        {supplier.name || 'N/A'}
                                                    </Typography>
                                                </Box>
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                    {supplier.identification_code || 'N/A'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                    <LocationOnIcon fontSize="small" color="action" />
                                                    <Typography variant="body2">
                                                        {supplier.country || 'N/A'}
                                                    </Typography>
                                                </Box>
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2">
                                                    {supplier.city_or_region || 'N/A'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                                    {supplier.telephone && (
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                            <PhoneIcon fontSize="small" color="action" />
                                                            <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                                                                {supplier.telephone}
                                                            </Typography>
                                                        </Box>
                                                    )}
                                                    {supplier.email && (
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                            <EmailIcon fontSize="small" color="action" />
                                                            <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                                                                {supplier.email}
                                                            </Typography>
                                                        </Box>
                                                    )}
                                                    {supplier.website && supplier.website !== 'http://' && (
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                            <LanguageIcon fontSize="small" color="action" />
                                                            <Typography
                                                                variant="body2"
                                                                sx={{ fontSize: '0.85rem' }}
                                                                component="a"
                                                                href={supplier.website}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                            >
                                                                Website
                                                            </Typography>
                                                        </Box>
                                                    )}
                                                </Box>
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={item.supplier.supplier_or_buyer_type || 'N/A'}
                                                    size="small"
                                                    color="primary"
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2">
                                                    {item.supplier.registration_date || 'N/A'}
                                                </Typography>
                                            </TableCell>
                                        </TableRow>
                                    )
                                })
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', px: 2 }}>
                    <Typography variant="body2" color="textSecondary" sx={{ mr: 2 }}>
                        Page {page + 1} of {Math.ceil(totalSuppliers / rowsPerPage)}
                    </Typography>
                    <TablePagination
                        rowsPerPageOptions={[10, 15, 20, 50, 100]}
                        component="div"
                        count={totalSuppliers}
                        rowsPerPage={rowsPerPage}
                        page={page}
                        onPageChange={handleChangePage}
                        onRowsPerPageChange={handleChangeRowsPerPage}
                        showFirstButton
                        showLastButton
                        sx={{ border: 'none' }}
                    />
                </Box>
            </Paper>

            {/* Supplier Detail Dialog */}
            <Dialog
                open={dialogOpen}
                onClose={handleCloseDialog}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6">Supplier Details</Typography>
                    <IconButton onClick={handleCloseDialog} size="small">
                        <CloseIcon />
                    </IconButton>
                </DialogTitle>
                <DialogContent dividers>
                    {selectedSupplier && (
                        <Box>
                            <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                Complete JSON Data:
                            </Typography>
                            <Paper
                                elevation={0}
                                sx={{
                                    p: 2,
                                    bgcolor: 'grey.50',
                                    maxHeight: '500px',
                                    overflow: 'auto',
                                    fontFamily: 'monospace',
                                    fontSize: '0.875rem'
                                }}
                            >
                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                    {JSON.stringify(selectedSupplier.supplier, null, 2)}
                                </pre>
                            </Paper>
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseDialog} variant="contained">
                        Close
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default Suppliers
