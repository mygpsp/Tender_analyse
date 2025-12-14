import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableSortLabel,
  TableRow,
  Paper,
  TextField,
  Pagination,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
  Stack,
  Grid,
  Card,
  CardContent,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Link,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import SearchIcon from '@mui/icons-material/Search'
import CloseIcon from '@mui/icons-material/Close'
import FilterListIcon from '@mui/icons-material/FilterList'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import TableChartIcon from '@mui/icons-material/TableChart'
import DescriptionIcon from '@mui/icons-material/Description'
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile'
import VisibilityIcon from '@mui/icons-material/Visibility'
import DownloadIcon from '@mui/icons-material/Download'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
// @ts-ignore - xlsx types may not be perfect
import * as XLSX from 'xlsx'
import { tendersApi, analyticsApi, detailedTendersApi } from '../services/api'
import type { TenderListResponse, TenderResponse, AnalyticsSummary, DetailedTender } from '../services/api'

export default function Tenders() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tenders, setTenders] = useState<TenderListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [tenderNumber, setTenderNumber] = useState('')
  const [buyer, setBuyer] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [filterByPublishedDate, setFilterByPublishedDate] = useState(true)
  const [filterByDeadlineDate, setFilterByDeadlineDate] = useState(true)
  const [amountMin, setAmountMin] = useState('')
  const [amountMax, setAmountMax] = useState('')
  const [hasDetailedData, setHasDetailedData] = useState<boolean | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [selectedTender, setSelectedTender] = useState<TenderResponse | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [selectedTenderNumbers, setSelectedTenderNumbers] = useState<Set<string>>(new Set())
  const [detailedData, setDetailedData] = useState<DetailedTender | null>(null)
  const [loadingDetailed, setLoadingDetailed] = useState(false)
  const [tenderNumbersWithDetails, setTenderNumbersWithDetails] = useState<Set<string>>(new Set())
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    bids: false,
    contracts: false,
    debug: false,
    basicInfo: true,
    dates: true,
    financial: true,
    requirements: true,
    description: false,
    specifications: false,
    documents: false,
    timeline: false,
    contacts: false,
    terms: false,
    additional: false,
    tabs: false,
    fullText: false,
  })
  const [debugExpanded, setDebugExpanded] = useState(false)
  const [groupBy, setGroupBy] = useState<'none' | 'category' | 'buyer'>('none')
  const [allFilteredTenders, setAllFilteredTenders] = useState<TenderResponse[]>([])
  const [loadingGroupedData, setLoadingGroupedData] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<{ name: string; tenders: TenderResponse[] } | null>(null)
  const [groupSortBy, setGroupSortBy] = useState<'count-desc' | 'count-asc' | 'amount-desc' | 'amount-asc'>('count-desc')
  const [similarTenders, setSimilarTenders] = useState<TenderListResponse | null>(null)
  const [loadingSimilar, setLoadingSimilar] = useState(false)
  const [similarDialogOpen, setSimilarDialogOpen] = useState(false)

  // Sorting
  const [sortBy, setSortBy] = useState('deadline_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  // Deep Search State
  const [deepSearchOpen, setDeepSearchOpen] = useState(false)
  const [deepSearchQuery, setDeepSearchQuery] = useState('')
  const [deepSearchResults, setDeepSearchResults] = useState<DetailedTender[]>([])
  const [searchingDeep, setSearchingDeep] = useState(false)

  // Load selected tenders from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('selectedTenderNumbers')
    if (saved) {
      try {
        const numbers = JSON.parse(saved)
        setSelectedTenderNumbers(new Set(numbers))
      } catch (e) {
        console.error('Failed to load selected tenders from localStorage', e)
      }
    }
  }, [])

  // Save selected tenders to localStorage when they change
  useEffect(() => {
    if (selectedTenderNumbers.size > 0) {
      localStorage.setItem('selectedTenderNumbers', JSON.stringify(Array.from(selectedTenderNumbers)))
    } else {
      localStorage.removeItem('selectedTenderNumbers')
    }
  }, [selectedTenderNumbers])

  // Function to reload tender numbers with detailed data
  const reloadTenderNumbersWithDetails = async () => {
    try {
      const data = await detailedTendersApi.getTenderNumbers()
      setTenderNumbersWithDetails(new Set(data.tender_numbers.map(n => n.toUpperCase())))
    } catch (err) {
      console.error('Failed to load tender numbers with detailed data', err)
    }
  }

  // Load tender numbers with detailed data on mount
  useEffect(() => {
    reloadTenderNumbersWithDetails()
  }, [])

  // Read URL parameters on mount
  useEffect(() => {
    const urlSearch = searchParams.get('search') || ''
    const urlTenderNumber = searchParams.get('tender_number') || ''
    const urlBuyer = searchParams.get('buyer') || ''
    const urlCategory = searchParams.get('category') || ''
    const urlStatus = searchParams.get('status') || ''
    const urlDateFrom = searchParams.get('date_from') || ''
    const urlDateTo = searchParams.get('date_to') || ''
    const urlFilterByPublished = searchParams.get('filter_by_published') !== 'false'
    const urlFilterByDeadline = searchParams.get('filter_by_deadline') !== 'false'
    const urlAmountMin = searchParams.get('amount_min') || ''
    const urlAmountMax = searchParams.get('amount_max') || ''
    const urlHasDetailedData = searchParams.get('has_detailed_data')

    setSearch(urlSearch)
    setTenderNumber(urlTenderNumber)
    setBuyer(urlBuyer)
    setCategory(urlCategory)
    setStatus(urlStatus)
    setDateFrom(urlDateFrom)
    setDateTo(urlDateTo)
    setFilterByPublishedDate(urlFilterByPublished)
    setFilterByDeadlineDate(urlFilterByDeadline)
    setAmountMin(urlAmountMin)
    setAmountMax(urlAmountMax)
    setAmountMin(urlAmountMin)
    setAmountMax(urlAmountMax)
    setHasDetailedData(urlHasDetailedData === 'true' ? true : urlHasDetailedData === 'false' ? false : null)

    const urlSortBy = searchParams.get('sort_by')
    const urlSortOrder = searchParams.get('sort_order')
    if (urlSortBy) setSortBy(urlSortBy)
    if (urlSortOrder) setSortOrder(urlSortOrder as 'asc' | 'desc')

    // Open filters if any are set
    if (urlTenderNumber || urlBuyer || urlCategory || urlStatus || urlDateFrom || urlDateTo || urlAmountMin || urlAmountMax || urlHasDetailedData || !urlFilterByPublished || !urlFilterByDeadline) {
      setFiltersOpen(true)
    }
  }, [searchParams])

  const loadTenders = async () => {
    try {
      setLoading(true)

      // Read current URL params directly to ensure we use the latest values
      // This is important when navigating from other pages
      const currentSearch = searchParams.get('search') || ''
      const currentTenderNumber = searchParams.get('tender_number') || ''
      const currentBuyer = searchParams.get('buyer') || ''
      const currentCategory = searchParams.get('category') || ''
      const currentStatus = searchParams.get('status') || ''
      const currentDateFrom = searchParams.get('date_from') || ''
      const currentDateTo = searchParams.get('date_to') || ''
      const currentFilterByPublished = searchParams.get('filter_by_published') !== 'false'
      const currentFilterByDeadline = searchParams.get('filter_by_deadline') !== 'false'
      const currentAmountMin = searchParams.get('amount_min') || ''
      const currentAmountMax = searchParams.get('amount_max') || ''
      const currentHasDetailedData = searchParams.get('has_detailed_data')

      // Build search query - combine category with search if both exist
      let searchQuery = currentSearch
      if (currentCategory && !currentSearch.includes(currentCategory)) {
        searchQuery = currentSearch ? `${currentSearch} ${currentCategory}` : currentCategory
      }

      const amountMinNum = currentAmountMin ? parseFloat(currentAmountMin) : undefined
      const amountMaxNum = currentAmountMax ? parseFloat(currentAmountMax) : undefined
      const hasDetailedDataBool = currentHasDetailedData === 'true' ? true : currentHasDetailedData === 'false' ? false : undefined

      // Build API params
      const apiParams: any = {
        page,
        page_size: 20,
        search: searchQuery || undefined,
        tender_number: currentTenderNumber || undefined,
        buyer: currentBuyer || undefined,
        status: currentStatus || undefined,
        amount_min: amountMinNum,
        amount_max: amountMaxNum,
        has_detailed_data: hasDetailedDataBool,
        sort_by: sortBy,
        sort_order: sortOrder,
      }

      // Only add date filters if dates are set
      if (currentDateFrom || currentDateTo) {
        apiParams.date_from = currentDateFrom || undefined
        apiParams.date_to = currentDateTo || undefined
        apiParams.filter_by_published_date = currentFilterByPublished
        apiParams.filter_by_deadline_date = currentFilterByDeadline
      }

      console.log('Calling API with params:', apiParams)
      const data = await tendersApi.list(apiParams)
      console.log('API response:', {
        total: data.total,
        items: data.items?.length,
        page: data.page,
        pages: data.pages
      })

      setTenders(data)

      // Load summary statistics with same filters (for accurate totals)
      // Use the same filters from URL params to ensure consistency
      try {
        const summaryData = await analyticsApi.summary({
          search: searchQuery || undefined,
          buyer: currentBuyer || undefined,
          status: currentStatus || undefined,
          date_from: currentDateFrom || undefined,
          date_to: currentDateTo || undefined,
          ...(currentDateFrom || currentDateTo ? {
            filter_by_published_date: currentFilterByPublished,
            filter_by_deadline_date: currentFilterByDeadline,
          } : {}),
          amount_min: amountMinNum,
          amount_max: amountMaxNum,
          // Note: tender_number filter not available in summary endpoint yet
        })
        setSummary(summaryData)
      } catch (err) {
        // Ignore summary errors, use page-level stats as fallback
        setSummary(null)
      }

      setError(null)
    } catch (err) {
      console.error('Error loading tenders:', err)
      setError(err instanceof Error ? err.message : 'Failed to load tenders')
      setTenders(null) // Clear tenders on error
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTenders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, searchParams]) // Use searchParams to react to URL changes, and page for pagination

  const clearFilters = () => {
    setSearch('')
    setTenderNumber('')
    setBuyer('')
    setCategory('')
    setStatus('')
    setDateFrom('')
    setDateTo('')
    setAmountMin('')
    setAmountMax('')
    setHasDetailedData(null)
    setSearchParams({})
    setPage(1)
  }

  const handleSearch = () => {
    setPage(1)
    // Update URL params
    const newParams = new URLSearchParams()
    if (search) newParams.set('search', search)
    if (tenderNumber) newParams.set('tender_number', tenderNumber)
    if (buyer) newParams.set('buyer', buyer)
    if (category) newParams.set('category', category)
    if (status) newParams.set('status', status)
    if (dateFrom) newParams.set('date_from', dateFrom)
    if (dateTo) newParams.set('date_to', dateTo)
    if (!filterByPublishedDate) newParams.set('filter_by_published', 'false')
    if (!filterByDeadlineDate) newParams.set('filter_by_deadline', 'false')
    if (amountMin) newParams.set('amount_min', amountMin)
    if (amountMax) newParams.set('amount_max', amountMax)
    if (hasDetailedData !== null) {
      newParams.set('has_detailed_data', hasDetailedData.toString())
    }
    newParams.set('sort_by', sortBy)
    newParams.set('sort_order', sortOrder)
    setSearchParams(newParams)
  }

  const handleShowActiveTenders = () => {
    // Get today's date in YYYY-MM-DD format
    const today = new Date().toISOString().split('T')[0]

    // Set filters for active tenders (deadline from today onwards)
    setDateFrom(today)
    setDateTo('') // No end date
    setFilterByPublishedDate(false)
    setFilterByDeadlineDate(true)
    setPage(1)

    // Update URL params
    const newParams = new URLSearchParams()
    newParams.set('date_from', today)
    newParams.set('filter_by_published', 'false')
    newParams.set('filter_by_deadline', 'true')

    // Preserve other filters if they exist
    if (search) newParams.set('search', search)
    if (tenderNumber) newParams.set('tender_number', tenderNumber)
    if (buyer) newParams.set('buyer', buyer)
    if (category) newParams.set('category', category)
    if (status) newParams.set('status', status)
    if (amountMin) newParams.set('amount_min', amountMin)
    if (amountMax) newParams.set('amount_max', amountMax)
    if (hasDetailedData !== null) {
      newParams.set('has_detailed_data', hasDetailedData.toString())
    }

    setSearchParams(newParams)
    setFiltersOpen(true) // Open filters to show what was applied
  }

  // Calculate statistics from current page items
  const calculateStats = () => {
    if (!tenders?.items) {
      return {
        totalTenders: 0,
        totalAmount: 0,
        avgAmount: 0,
        tendersWithAmount: 0,
        pageTotal: 0,
      }
    }

    let totalAmount = 0
    let tendersWithAmount = 0

    tenders.items.forEach((item) => {
      // Use structured amount field if available, otherwise extract from all_cells (backward compatibility)
      const amount = item.tender.amount ?? extractAmount(item.tender.all_cells || item.tender.buyer || '')
      if (amount) {
        totalAmount += amount
        tendersWithAmount++
      }
    })

    return {
      totalTenders: tenders.total, // Total filtered tenders from backend
      totalAmount, // Sum of amounts on current page
      avgAmount: tendersWithAmount > 0 ? totalAmount / tendersWithAmount : 0,
      tendersWithAmount,
      pageTotal: tenders.items.length, // Items on current page
    }
  }

  // Load all filtered tenders for grouping
  const loadAllFilteredTenders = async () => {
    if (groupBy === 'none') {
      setAllFilteredTenders([])
      return
    }

    setLoadingGroupedData(true)
    try {
      const currentSearch = searchParams.get('search') || ''
      const currentTenderNumber = searchParams.get('tender_number') || ''
      const currentBuyer = searchParams.get('buyer') || ''
      const currentCategory = searchParams.get('category') || ''
      const currentStatus = searchParams.get('status') || ''
      const currentDateFrom = searchParams.get('date_from') || ''
      const currentDateTo = searchParams.get('date_to') || ''
      const currentFilterByPublished = searchParams.get('filter_by_published') !== 'false'
      const currentFilterByDeadline = searchParams.get('filter_by_deadline') !== 'false'
      const currentAmountMin = searchParams.get('amount_min') || ''
      const currentAmountMax = searchParams.get('amount_max') || ''
      const currentHasDetailedData = searchParams.get('has_detailed_data')

      let searchQuery = currentSearch
      if (currentCategory && !currentSearch.includes(currentCategory)) {
        searchQuery = currentSearch ? `${currentSearch} ${currentCategory}` : currentCategory
      }

      const amountMinNum = currentAmountMin ? parseFloat(currentAmountMin) : undefined
      const amountMaxNum = currentAmountMax ? parseFloat(currentAmountMax) : undefined
      const hasDetailedDataBool = currentHasDetailedData === 'true' ? true : currentHasDetailedData === 'false' ? false : undefined

      // Fetch all pages
      const allData = await tendersApi.list({
        page: 1,
        page_size: 10000, // Large number to get all
        search: searchQuery || undefined,
        tender_number: currentTenderNumber || undefined,
        buyer: currentBuyer || undefined,
        status: currentStatus || undefined,
        date_from: currentDateFrom || undefined,
        date_to: currentDateTo || undefined,
        ...(currentDateFrom || currentDateTo ? {
          filter_by_published_date: currentFilterByPublished,
          filter_by_deadline_date: currentFilterByDeadline,
        } : {}),
        amount_min: amountMinNum,
        amount_max: amountMaxNum,
        has_detailed_data: hasDetailedDataBool,
      })

      console.log('Fetched tenders for grouping:', allData.items.length, 'items')
      setAllFilteredTenders(allData.items)
    } catch (err) {
      console.error('Failed to load all filtered tenders for grouping:', err)
      setAllFilteredTenders([])
    } finally {
      setLoadingGroupedData(false)
    }
  }

  // Load all filtered tenders when groupBy changes
  useEffect(() => {
    if (groupBy !== 'none') {
      console.log('Loading all filtered tenders for grouping, groupBy:', groupBy)
      loadAllFilteredTenders()
    } else {
      setAllFilteredTenders([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupBy])

  // Calculate grouped statistics
  const calculateGroupedStats = () => {
    console.log('calculateGroupedStats called, groupBy:', groupBy, 'allFilteredTenders.length:', allFilteredTenders.length)
    if (groupBy === 'none' || allFilteredTenders.length === 0) {
      return null
    }

    const groups: Record<string, { count: number; totalAmount: number; tenders: TenderResponse[] }> = {}

    allFilteredTenders.forEach((item) => {
      const allCells = item.tender.all_cells || item.tender.buyer || ''
      const amount = item.tender.amount ?? extractAmount(allCells)

      let groupKey = 'N/A'
      if (groupBy === 'category') {
        groupKey = item.tender.category || extractCategory(allCells)
      } else if (groupBy === 'buyer') {
        groupKey = item.tender.buyer || extractBuyerName(allCells)
      }

      if (!groups[groupKey]) {
        groups[groupKey] = { count: 0, totalAmount: 0, tenders: [] }
      }

      groups[groupKey].count++
      if (amount) {
        groups[groupKey].totalAmount += amount
      }
      groups[groupKey].tenders.push(item)
    })

    // Convert to array
    const groupsArray = Object.entries(groups)
      .map(([name, data]) => ({
        name,
        count: data.count,
        totalAmount: data.totalAmount,
        avgAmount: data.totalAmount / data.count,
        tenders: data.tenders,
      }))

    // Sort based on groupSortBy
    groupsArray.sort((a, b) => {
      switch (groupSortBy) {
        case 'count-desc':
          return b.count - a.count
        case 'count-asc':
          return a.count - b.count
        case 'amount-desc':
          return b.totalAmount - a.totalAmount
        case 'amount-asc':
          return a.totalAmount - b.totalAmount
        default:
          return b.count - a.count
      }
    })

    return groupsArray
  }

  const handleTenderClick = async (tender: TenderResponse) => {
    setSelectedTender(tender)
    // Reset accordion states when opening dialog
    setExpandedSections({
      debug: false,
      basicInfo: true,
      dates: true,
      financial: true,
      requirements: true,
      description: false,
      specifications: false,
      documents: false,
      timeline: false,
      contacts: false,
      terms: false,
      additional: false,
      tabs: false,
      fullText: false,
      bids: false,
      contracts: false,
    })
    setDebugExpanded(false)
    setDialogOpen(true)

    // Try to load detailed data
    const tenderNum = extractTenderNumber(tender.tender.number || tender.tender.all_cells || '')
    if (tenderNum) {
      setLoadingDetailed(true)
      try {
        // Reload backend cache first to ensure we have latest data
        await detailedTendersApi.reload()
        const detailed = await detailedTendersApi.getByTenderNumber(tenderNum)
        console.log('✅ Loaded detailed data:', {
          tender_number: detailed.tender_number || detailed.procurement_number || detailed.number,
          has_tabs_data: !!detailed.tabs_data,
          tabs_count: detailed.tabs_data ? Object.keys(detailed.tabs_data).length : 0,
          has_bids: detailed.bids && detailed.bids.length > 0,
          bids_count: detailed.bids ? detailed.bids.length : 0,
          status: detailed.status
        })
        setDetailedData(detailed)
      } catch (err: any) {
        console.error('❌ Failed to load detailed data:', err)
        console.error('   Tender number used:', tenderNum)
        console.error('   Error details:', err.response?.data || err.message)
        // Detailed data not available - that's okay
        setDetailedData(null)
      } finally {
        setLoadingDetailed(false)
      }
    } else {
      console.warn('⚠️ Could not extract tender number from:', tender.tender.number || tender.tender.all_cells)
    }
  }

  const handleDeleteDetailedData = async () => {
    const tenderNum = detailedData?.tender_number || detailedData?.procurement_number || detailedData?.number
    if (!tenderNum) return

    setDeleting(true)
    try {
      const tenderNum = detailedData.tender_number || detailedData.procurement_number || detailedData.number
      await detailedTendersApi.delete(tenderNum)

      // Remove from local state
      setDetailedData(null)

      // Reload tender numbers with details from backend to ensure consistency
      // This ensures the filter and badges are updated correctly
      await reloadTenderNumbersWithDetails()

      // Reload tenders to update the "Detailed" badge and filter results
      // This will use the updated backend cache which no longer includes the deleted tender
      await loadTenders()

      setDeleteConfirmOpen(false)
      setError(null)
    } catch (err) {
      console.error('Failed to delete detailed data:', err)
      setError(err instanceof Error ? err.message : 'Failed to delete detailed data')
    } finally {
      setDeleting(false)
    }
  }

  const extractTenderNumber = (text: string) => {
    const match = text.match(/([A-Z]{2,4}\d{9,})/)
    return match ? match[1] : text.substring(0, 30)
  }

  const handleFindSimilar = async () => {
    if (!selectedTender) return

    setLoadingSimilar(true)
    try {
      const similar = await tendersApi.getSimilar(selectedTender.id, 50)
      setSimilarTenders(similar)
      setSimilarDialogOpen(true)
    } catch (err) {
      console.error('Failed to load similar tenders:', err)
      setError(err instanceof Error ? err.message : 'Failed to load similar tenders')
    } finally {
      setLoadingSimilar(false)
    }
  }

  const handleDeepSearch = async () => {
    if (!deepSearchQuery.trim()) return

    setSearchingDeep(true)
    try {
      const results = await detailedTendersApi.search(deepSearchQuery)
      setDeepSearchResults(results)
    } catch (err) {
      console.error('Failed to search detailed tenders:', err)
      setError(err instanceof Error ? err.message : 'Failed to search detailed tenders')
    } finally {
      setSearchingDeep(false)
    }
  }

  // Remove duplicated content from tabs_data and full_text that's already in basic_info
  const deduplicateContent = (detailedData: DetailedTender | null): DetailedTender | null => {
    if (!detailedData || !detailedData.basic_info) {
      return detailedData
    }

    // Collect all values from basic_info to check for duplicates
    const basicInfoValues = new Set<string>()
    Object.values(detailedData.basic_info).forEach((value) => {
      if (typeof value === 'string' && value.trim()) {
        // Add the full value
        basicInfoValues.add(value.trim())
        // Also add key parts (for dates, amounts, etc.)
        const parts = value.split(/\s+/).filter(p => p.length > 3)
        parts.forEach(part => basicInfoValues.add(part))
      } else if (Array.isArray(value)) {
        value.forEach((item: string) => {
          if (typeof item === 'string' && item.trim()) {
            basicInfoValues.add(item.trim())
          }
        })
      }
    })

    // Filter tabs_data - remove tabs that only contain basic_info content
    let filteredTabsData: Record<string, { text: string; html: string }> | undefined
    if (detailedData.tabs_data) {
      filteredTabsData = {}
      Object.entries(detailedData.tabs_data).forEach(([tabName, tabContent]) => {
        const textContent = typeof tabContent === 'object' ? (tabContent.text || tabContent.html || '') : String(tabContent || '')

        // Check if this tab content is mostly duplicate of basic_info
        const textWords = textContent.split(/\s+/).filter(w => w.length > 3)
        const duplicateCount = textWords.filter(word => {
          // Check if word or similar appears in basic_info
          return Array.from(basicInfoValues).some(basicValue =>
            basicValue.includes(word) || word.includes(basicValue) ||
            basicValue.toLowerCase().includes(word.toLowerCase()) ||
            word.toLowerCase().includes(basicValue.toLowerCase())
          )
        }).length

        // If less than 30% is new content, consider it duplicate
        const duplicateRatio = textWords.length > 0 ? duplicateCount / textWords.length : 0
        if (duplicateRatio < 0.7 || textContent.length < 100) {
          // Keep this tab - it has significant new content
          filteredTabsData[tabName] = typeof tabContent === 'object' ? tabContent : { text: textContent, html: textContent }
        }
      })

      // If all tabs were filtered out, keep original
      if (Object.keys(filteredTabsData).length === 0) {
        filteredTabsData = detailedData.tabs_data
      }
    }

    // Filter full_text - remove sections that duplicate basic_info
    let filteredFullText: string | undefined
    if (detailedData.full_text) {
      const fullTextLines = detailedData.full_text.split('\n')
      const filteredLines: string[] = []

      fullTextLines.forEach((line) => {
        const trimmedLine = line.trim()
        if (!trimmedLine) {
          filteredLines.push(line) // Keep empty lines for formatting
          return
        }

        // Check if this line is duplicate of basic_info
        const lineWords = trimmedLine.split(/\s+/).filter(w => w.length > 3)
        if (lineWords.length === 0) {
          filteredLines.push(line)
          return
        }

        const duplicateCount = lineWords.filter(word => {
          return Array.from(basicInfoValues).some(basicValue =>
            basicValue.includes(word) || word.includes(basicValue) ||
            basicValue.toLowerCase().includes(word.toLowerCase()) ||
            word.toLowerCase().includes(basicValue.toLowerCase())
          )
        }).length

        // If less than 50% is duplicate, keep the line
        const duplicateRatio = lineWords.length > 0 ? duplicateCount / lineWords.length : 0
        if (duplicateRatio < 0.5) {
          filteredLines.push(line)
        }
      })

      filteredFullText = filteredLines.join('\n')

      // If filtered text is too short, keep original
      if (filteredFullText.length < detailedData.full_text.length * 0.3) {
        filteredFullText = detailedData.full_text
      }
    }

    return {
      ...detailedData,
      tabs_data: filteredTabsData,
      full_text: filteredFullText
    }
  }

  const handleToggleSelection = (tenderNumber: string, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent row click
    setSelectedTenderNumbers((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(tenderNumber)) {
        newSet.delete(tenderNumber)
      } else {
        newSet.add(tenderNumber)
      }
      return newSet
    })
  }

  const handleSelectAll = () => {
    if (!tenders?.items) return
    const allNumbers = new Set(
      tenders.items.map((item) => {
        const allCells = item.tender.all_cells || item.tender.number || ''
        return extractTenderNumber(allCells)
      }).filter(Boolean)
    )
    setSelectedTenderNumbers(allNumbers)
  }

  const handleDeselectAll = () => {
    setSelectedTenderNumbers(new Set())
  }

  const handleSelectAllFiltered = async () => {
    // Get all filtered tenders (not just current page)
    try {
      const currentSearch = searchParams.get('search') || ''
      const currentTenderNumber = searchParams.get('tender_number') || ''
      const currentBuyer = searchParams.get('buyer') || ''
      const currentCategory = searchParams.get('category') || ''
      const currentStatus = searchParams.get('status') || ''
      const currentDateFrom = searchParams.get('date_from') || ''
      const currentDateTo = searchParams.get('date_to') || ''
      const currentAmountMin = searchParams.get('amount_min') || ''
      const currentAmountMax = searchParams.get('amount_max') || ''

      let searchQuery = currentSearch
      if (currentCategory && !currentSearch.includes(currentCategory)) {
        searchQuery = currentSearch ? `${currentSearch} ${currentCategory}` : currentCategory
      }

      const amountMinNum = currentAmountMin ? parseFloat(currentAmountMin) : undefined
      const amountMaxNum = currentAmountMax ? parseFloat(currentAmountMax) : undefined

      // Get all pages (use large page_size to get all at once)
      const allData = await tendersApi.list({
        page: 1,
        page_size: 10000, // Large number to get all
        search: searchQuery || undefined,
        tender_number: currentTenderNumber || undefined,
        buyer: currentBuyer || undefined,
        status: currentStatus || undefined,
        date_from: currentDateFrom || undefined,
        date_to: currentDateTo || undefined,
        ...(currentDateFrom || currentDateTo ? {
          filter_by_published_date: currentFilterByPublished,
          filter_by_deadline_date: currentFilterByDeadline,
        } : {}),
        amount_min: amountMinNum,
        amount_max: amountMaxNum,
      })

      const allNumbers = new Set(
        allData.items.map((item) => {
          const allCells = item.tender.all_cells || item.tender.number || ''
          return extractTenderNumber(allCells)
        }).filter(Boolean)
      )
      setSelectedTenderNumbers(allNumbers)
    } catch (err) {
      console.error('Failed to select all filtered tenders', err)
    }
  }

  const extractBuyerName = (text: string): string => {
    if (!text) return 'N/A'

    // Look for pattern: შემსყიდველი: <name> or შემსყიდველი: <strong>name</strong>
    const patterns = [
      /შემსყიდველი:\s*<strong>([^<]+)<\/strong>/,
      /შემსყიდველი:\s*([^\n]+)/,
    ]

    for (const pattern of patterns) {
      const match = text.match(pattern)
      if (match && match[1]) {
        let name = match[1].trim()
        // Remove HTML tags if any
        name = name.replace(/<[^>]+>/g, '').trim()
        if (name && name.length > 0) {
          return name
        }
      }
    }

    // Fallback: return first 50 chars if no pattern matches
    return text.substring(0, 50) || 'N/A'
  }

  const extractCategory = (text: string): string => {
    if (!text) return 'N/A'

    // Look for CPV code pattern: 14200000-ქვიშა და თიხა
    const pattern = /(\d{8})-\s*([^\n]+)/
    const match = text.match(pattern)
    if (match) {
      return `${match[1]}-${match[2].trim()}`
    }

    // Look for "კატეგორია:" pattern
    const categoryPattern = /კატეგორია[:\s]+([^\n]+)/
    const categoryMatch = text.match(categoryPattern)
    if (categoryMatch) {
      let category = categoryMatch[1].trim()
      category = category.replace(/<[^>]+>/g, '').trim()
      if (category) return category
    }

    return 'N/A'
  }

  const extractAmount = (text: string): number | null => {
    if (!text) return null

    // Look for amount pattern: 17`627.00 ლარი
    const patterns = [
      /(\d+(?:`\d+)*(?:\.\d+)?)\s*ლარი/,
      /ღირებულება[:\s]+(\d+(?:`\d+)*(?:\.\d+)?)/,
      /(\d+(?:`\d+)+\.\d+)/,
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

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'decimal',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount) + ' GEL'
  }

  const handleExportToExcel = async () => {
    try {
      // Warn user if filters are active
      const hasFilters = !!(buyer || status || dateFrom || dateTo || search || amountMin || amountMax || tenderNumber || hasDetailedData !== null)
      if (hasFilters) {
        const confirmed = window.confirm(
          `⚠️ Filters are currently active. The export will include only filtered results.\n\n` +
          `Active filters:\n` +
          `${buyer ? `- Buyer: ${buyer}\n` : ''}` +
          `${status ? `- Status: ${status}\n` : ''}` +
          `${dateFrom || dateTo ? `- Date Range: ${dateFrom || '...'} to ${dateTo || '...'}\n` : ''}` +
          `${amountMin || amountMax ? `- Amount: ${amountMin || '...'} to ${amountMax || '...'}\n` : ''}` +
          `${tenderNumber ? `- Tender Number: ${tenderNumber}\n` : ''}` +
          `${hasDetailedData !== null ? `- Has Detailed Data: ${hasDetailedData}\n` : ''}` +
          `${search ? `- Search: ${search}\n` : ''}` +
          `\nClick OK to export filtered data, or Cancel to clear filters and export all data.`
        )
        if (!confirmed) {
          return
        }
      }

      setLoading(true)

      // Load all tenders (not just current page) with current filters
      const allTenders: TenderResponse[] = []
      let page = 1
      let hasMore = true
      const pageSize = 100

      while (hasMore) {
        const response = await tendersApi.list({
          page,
          page_size: pageSize,
          buyer: buyer || undefined,
          status: status || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          ...(dateFrom || dateTo ? {
            filter_by_published_date: filterByPublishedDate,
            filter_by_deadline_date: filterByDeadlineDate,
          } : {}),
          search: search || undefined,
          amount_min: amountMin ? parseFloat(amountMin) : undefined,
          amount_max: amountMax ? parseFloat(amountMax) : undefined,
          tender_number: tenderNumber || undefined,
          has_detailed_data: hasDetailedData !== null ? hasDetailedData : undefined,
        })
        allTenders.push(...response.items)
        hasMore = response.page < response.pages
        page++
      }

      if (allTenders.length === 0) {
        alert('No tenders to export.')
        setLoading(false)
        return
      }

      // Prepare data for Excel - include all fields from JSON
      // IMPORTANT: Use EXACT same logic as frontend Tenders page table display
      // Frontend table uses: const amount = item.tender.amount ?? extractAmount(allCells)
      // Where allCells = item.tender.all_cells || item.tender.buyer || ''
      // This ensures Excel values match exactly what user sees in the frontend table

      let totalAmount = 0
      let tendersWithAmount = 0

      const excelData = allTenders.map((item, index) => {
        const tender = item.tender

        // EXACT COPY of frontend table logic (line 1311-1315):
        // const allCells = item.tender.all_cells || item.tender.buyer || ''
        // const amount = item.tender.amount ?? extractAmount(allCells)
        const allCells = tender.all_cells || tender.buyer || ''
        const amount = tender.amount ?? extractAmount(allCells)

        // EXACT COPY of frontend calculateStats() logic (line 297-301):
        // if (amount) {
        //   totalAmount += amount
        //   tendersWithAmount++
        // }
        if (amount) {
          totalAmount += amount
          tendersWithAmount++
        }

        return {
          'Row Number': index + 1,
          'Tender Number': tender.number || '',
          'Tender Type': tender.tender_type || '',
          'Tender ID': tender.tender_id || '',
          'Buyer': tender.buyer || '',
          'Supplier': tender.supplier || '',
          'Status': tender.status || '',
          'Participants Count': tender.participants_count ?? null,
          // Amount uses EXACT same value as shown in frontend table cell (line 1380: formatCurrency(amount))
          'Amount (GEL)': amount,
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

      // Add summary row at the end
      // Note: This total uses the SAME calculation as frontend: amount ?? extractAmount(all_cells)
      const summaryRow: any = {
        'Row Number': '',
        'Tender Number': '=== SUMMARY (Matches Frontend Calculation) ===',
        'Tender Type': '',
        'Tender ID': '',
        'Buyer': '',
        'Supplier': '',
        'Status': '',
        'Participants Count': '',
        'Amount (GEL)': totalAmount, // This matches frontend calculateStats() total
        'Published Date': '',
        'Deadline Date': '',
        'Category Code': '',
        'Category': '',
        'Detail URL': '',
        'Scraped At': '',
        'Date Window From': '',
        'Date Window To': '',
        'Extraction Method': '',
        'All Cells Content': `CALCULATION METHOD: Uses same logic as frontend (tender.amount ?? extractAmount(all_cells)) | Total Records: ${allTenders.length} | Records with Amount: ${tendersWithAmount} | Total Amount (GEL): ${totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} | Note: Excel SUM() should match this value if all amounts are numeric`,
      }
      excelData.push(summaryRow)

      // Create workbook and worksheet
      const worksheet = XLSX.utils.json_to_sheet(excelData)
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Tenders')

      // Set column widths and format amount column as numeric
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

        // Format amount column as number with 2 decimal places
        const amountColIndex = Object.keys(excelData[0]).indexOf('Amount (GEL)')
        if (amountColIndex >= 0) {
          const amountColLetter = XLSX.utils.encode_col(amountColIndex)
          const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1')

          // Apply number format to all amount cells (except header)
          for (let row = 1; row <= range.e.r; row++) {
            const cellAddress = amountColLetter + (row + 1)
            if (worksheet[cellAddress]) {
              worksheet[cellAddress].z = '#,##0.00' // Number format with thousands separator and 2 decimals
            }
          }
        }
      }

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().split('T')[0]
      const filename = `tenders_export_${timestamp}.xlsx`

      // Write and download
      XLSX.writeFile(workbook, filename)
      setLoading(false)
    } catch (error) {
      console.error('Error exporting to Excel:', error)
      alert('Failed to export to Excel. Please try again.')
      setLoading(false)
    }
  }

  // Debug: Log current state
  console.log('Tenders component render:', {
    loading,
    error,
    tenders: tenders?.items?.length,
    page,
    hasTenders: !!tenders,
    hasItems: !!tenders?.items,
    itemsLength: tenders?.items?.length || 0
  })

  // Always render something - even if empty
  // CRITICAL: This header must always render to verify component is working
  return (
    <Box sx={{ p: 2, minHeight: '200px' }}>
      {/* Debug Info - Always show for troubleshooting */}
      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography variant="body2">
          <strong>Debug Info:</strong> loading={loading ? 'true' : 'false'},
          error={error || 'none'},
          tenders={tenders ? `${tenders.items?.length || 0} items (total: ${tenders.total})` : 'null'},
          page={page}
        </Typography>
      </Alert>

      {/* Header with Filter Toggle */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4" component="h1">
            Tenders
          </Typography>
          {selectedTenderNumbers.size > 0 && (
            <Typography variant="body2" color="textSecondary" sx={{ mt: 0.5 }}>
              {selectedTenderNumbers.size} tender{selectedTenderNumbers.size !== 1 ? 's' : ''} selected
            </Typography>
          )}
        </Box>
        <Stack direction="row" spacing={1}>
          {selectedTenderNumbers.size > 0 && (
            <>
              <Button
                variant="outlined"
                size="small"
                onClick={handleDeselectAll}
              >
                Deselect All
              </Button>
              <Button
                variant="contained"
                size="small"
                color="primary"
                onClick={() => navigate('/selection')}
              >
                View Selected ({selectedTenderNumbers.size})
              </Button>
            </>
          )}
          <Button
            variant="outlined"
            startIcon={filtersOpen ? <ExpandLessIcon /> : <FilterListIcon />}
            onClick={() => setFiltersOpen(!filtersOpen)}
          >
            {filtersOpen ? 'Hide Filters' : 'Show Filters'}
          </Button>
          <Button
            variant="contained"
            startIcon={<CalendarTodayIcon />}
            onClick={handleShowActiveTenders}
            color="primary"
          >
            Active Tenders
          </Button>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExportToExcel}
            color="success"
          >
            Export to Excel
          </Button>
          <Button
            variant="outlined"
            startIcon={<SearchIcon />}
            onClick={() => setDeepSearchOpen(true)}
          >
            Search in Detailed Data
          </Button>
        </Stack>
      </Box>

      {/* Filter Panel */}
      <Collapse in={filtersOpen}>
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Filters
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Search"
                placeholder="Search tenders, categories, numbers..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="განცხადების ნომერი (Tender Number)"
                placeholder="e.g., GEO250000579"
                value={tenderNumber}
                onChange={(e) => setTenderNumber(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                helperText="Enter tender number to filter (partial match supported)"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Buyer"
                placeholder="Filter by buyer name..."
                value={buyer}
                onChange={(e) => setBuyer(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Category"
                placeholder="Enter category or CPV code..."
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                helperText="e.g., 14200000 or 'ქვიშა და თიხა'"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={status}
                  label="Status"
                  onChange={(e) => setStatus(e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="გამოცხადებულია">გამოცხადებულია</MenuItem>
                  <MenuItem value="წინადადებების მიღება დაწყებულია">წინადადებების მიღება დაწყებულია</MenuItem>
                  <MenuItem value="წინადადებების მიღება დასრულებულია">წინადადებების მიღება დასრულებულია</MenuItem>
                  <MenuItem value="შერჩევა/შეფასება">შერჩევა/შეფასება</MenuItem>
                  <MenuItem value="გამარჯვებული გამოვლენილია">გამარჯვებული გამოვლენილია</MenuItem>
                  <MenuItem value="დასრულებულია უარყოფითი შედეგით">დასრულებულია უარყოფითი შედეგით</MenuItem>
                  <MenuItem value="არ შედგა">არ შედგა</MenuItem>
                  <MenuItem value="შეწყვეტილია">შეწყვეტილია</MenuItem>
                  <MenuItem value="მიმდინარეობს ხელშეკრულების მომზადება">მიმდინარეობს ხელშეკრულების მომზადება</MenuItem>
                  <MenuItem value="ხელშეკრულება დადებულია">ხელშეკრულება დადებულია</MenuItem>
                  <MenuItem value="დასრულებულია">დასრულებულია</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Date From"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Date To"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 1 }}>
                <Typography variant="body2" color="textSecondary">
                  Filter by:
                </Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={filterByPublishedDate}
                      onChange={(e) => setFilterByPublishedDate(e.target.checked)}
                      size="small"
                    />
                  }
                  label="Published Date"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={filterByDeadlineDate}
                      onChange={(e) => setFilterByDeadlineDate(e.target.checked)}
                      size="small"
                    />
                  }
                  label="Deadline Date"
                />
              </Box>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Amount Min (GEL)"
                type="number"
                value={amountMin}
                onChange={(e) => setAmountMin(e.target.value)}
                placeholder="0"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Amount Max (GEL)"
                type="number"
                value={amountMax}
                onChange={(e) => setAmountMax(e.target.value)}
                placeholder="1000000"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', pt: 1 }}>
                <Checkbox
                  checked={hasDetailedData === true}
                  indeterminate={hasDetailedData === null}
                  onChange={(e) => {
                    const newValue = e.target.checked ? true : null
                    setHasDetailedData(newValue)
                    // Update URL immediately to trigger reload
                    const newParams = new URLSearchParams(searchParams)
                    if (newValue !== null) {
                      newParams.set('has_detailed_data', newValue.toString())
                    } else {
                      newParams.delete('has_detailed_data')
                    }
                    setSearchParams(newParams)
                    setPage(1)
                  }}
                />
                <Typography variant="body2">
                  Show only tenders with detailed data
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                <Button variant="contained" onClick={handleSearch} startIcon={<SearchIcon />}>
                  Apply Filters
                </Button>
                <Button variant="outlined" onClick={clearFilters}>
                  Clear All
                </Button>
                <Button
                  variant="outlined"
                  onClick={handleSelectAllFiltered}
                  disabled={loading}
                >
                  Select All Filtered
                </Button>
                {selectedTenderNumbers.size > 0 && (
                  <Button
                    variant="outlined"
                    color="error"
                    onClick={handleDeselectAll}
                  >
                    Deselect All ({selectedTenderNumbers.size})
                  </Button>
                )}
              </Stack>
            </Grid>
          </Grid>
        </Paper>
      </Collapse>

      {/* Active Filters */}
      {(buyer || category || status || dateFrom || dateTo || search || tenderNumber || amountMin || amountMax || hasDetailedData !== null) && (
        <Box mb={2}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {tenderNumber && (
              <Chip
                label={`Tender Number: ${tenderNumber}`}
                onDelete={() => {
                  setTenderNumber('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('tender_number')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {buyer && (
              <Chip
                label={`Buyer: ${buyer}`}
                onDelete={() => {
                  setBuyer('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('buyer')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {dateFrom && (
              <Chip
                label={`From: ${dateFrom}`}
                onDelete={() => {
                  setDateFrom('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('date_from')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {dateTo && (
              <Chip
                label={`To: ${dateTo}`}
                onDelete={() => {
                  setDateTo('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('date_to')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {search && (
              <Chip
                label={`Search: ${search}`}
                onDelete={() => {
                  setSearch('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('search')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {category && (
              <Chip
                label={`Category: ${category}`}
                onDelete={() => {
                  setCategory('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('category')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {status && (
              <Chip
                label={`Status: ${status}`}
                onDelete={() => {
                  setStatus('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('status')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {amountMin && (
              <Chip
                label={`Amount ≥ ${formatCurrency(parseFloat(amountMin))}`}
                onDelete={() => {
                  setAmountMin('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('amount_min')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {amountMax && (
              <Chip
                label={`Amount ≤ ${formatCurrency(parseFloat(amountMax))}`}
                onDelete={() => {
                  setAmountMax('')
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('amount_max')
                  setSearchParams(newParams)
                }}
                size="small"
              />
            )}
            {hasDetailedData !== null && (
              <Chip
                label={hasDetailedData ? "With Detailed Data" : "Without Detailed Data"}
                onDelete={() => {
                  setHasDetailedData(null)
                  const newParams = new URLSearchParams(searchParams)
                  newParams.delete('has_detailed_data')
                  setSearchParams(newParams)
                }}
                size="small"
                color={hasDetailedData ? "success" : "default"}
              />
            )}
            <Chip
              label="Clear All"
              onDelete={clearFilters}
              size="small"
              color="error"
            />
          </Stack>
        </Box>
      )}

      {/* Data Availability Info */}
      {summary?.date_range && (
        <Alert
          severity="info"
          icon={<CalendarTodayIcon />}
          sx={{ mb: 2 }}
        >
          <Typography variant="body2">
            <strong>Data Available:</strong> From {summary.date_range.from} to {summary.date_range.to}
          </Typography>
        </Alert>
      )}

      {/* Group By Selector */}
      {(tenders || summary) && !loading && (
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2" color="textSecondary">
            Group by:
          </Typography>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <Select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as 'none' | 'category' | 'buyer')}
            >
              <MenuItem value="none">No Grouping</MenuItem>
              <MenuItem value="category">Category</MenuItem>
              <MenuItem value="buyer">Buyer</MenuItem>
            </Select>
          </FormControl>
        </Box>
      )}

      {/* Grouped Statistics Display */}
      {groupBy !== 'none' && (
        <Box sx={{ mb: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Grouped by {groupBy === 'category' ? 'Category' : 'Buyer'}
            </Typography>
            <Box display="flex" gap={1}>
              <Button
                size="small"
                variant={groupSortBy === 'count-desc' ? 'contained' : 'outlined'}
                onClick={() => setGroupSortBy('count-desc')}
              >
                Count ↓
              </Button>
              <Button
                size="small"
                variant={groupSortBy === 'count-asc' ? 'contained' : 'outlined'}
                onClick={() => setGroupSortBy('count-asc')}
              >
                Count ↑
              </Button>
              <Button
                size="small"
                variant={groupSortBy === 'amount-desc' ? 'contained' : 'outlined'}
                onClick={() => setGroupSortBy('amount-desc')}
              >
                Amount ↓
              </Button>
              <Button
                size="small"
                variant={groupSortBy === 'amount-asc' ? 'contained' : 'outlined'}
                onClick={() => setGroupSortBy('amount-asc')}
              >
                Amount ↑
              </Button>
            </Box>
          </Box>
          {loadingGroupedData ? (
            <Box display="flex" justifyContent="center" alignItems="center" p={4}>
              <CircularProgress size={24} sx={{ mr: 2 }} />
              <Typography>Loading all filtered tenders for grouping...</Typography>
            </Box>
          ) : calculateGroupedStats() ? (
            <>
              <Grid container spacing={1.5}>
                {calculateGroupedStats()!.map((group, index) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                    <Card
                      sx={{
                        cursor: 'pointer',
                        height: '100%',
                        '&:hover': {
                          boxShadow: 6,
                          transform: 'translateY(-2px)',
                          transition: 'all 0.2s'
                        }
                      }}
                      onClick={() => setSelectedGroup({ name: group.name, tenders: group.tenders })}
                    >
                      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                        <Typography
                          variant="body2"
                          color="textSecondary"
                          gutterBottom
                          sx={{
                            fontSize: '0.75rem',
                            lineHeight: 1.3,
                            minHeight: '2.6rem',
                            overflow: 'hidden',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            mb: 0.5
                          }}
                          title={group.name}
                        >
                          {group.name}
                        </Typography>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {group.count} tender{group.count !== 1 ? 's' : ''}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {formatCurrency(group.totalAmount)}
                          </Typography>
                        </Box>
                        <Typography variant="caption" color="textSecondary" display="block">
                          Avg: {formatCurrency(group.avgAmount)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
              {calculateGroupedStats()!.length > 20 && (
                <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                  Showing all {calculateGroupedStats()!.length} groups
                </Typography>
              )}
            </>
          ) : (
            <Typography variant="body2" color="textSecondary">
              No data available for grouping
            </Typography>
          )}
        </Box>
      )}

      {/* Statistics Cards - Always show if we have data or summary */}
      {(tenders || summary) && !loading && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  Total Tenders
                </Typography>
                <Typography variant="h5">
                  {calculateStats().totalTenders.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  Total Amount
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                  {summary?.total_amount
                    ? formatCurrency(summary.total_amount)
                    : formatCurrency(calculateStats().totalAmount)}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {summary?.total_amount ? '(All filtered)' : '(Current page)'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  Average Amount
                </Typography>
                <Typography variant="h5">
                  {summary?.avg_amount
                    ? formatCurrency(summary.avg_amount)
                    : formatCurrency(calculateStats().avgAmount)}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {summary?.avg_amount ? '(All filtered)' : '(Current page)'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  Showing
                </Typography>
                <Typography variant="h5">
                  {calculateStats().pageTotal} of {calculateStats().totalTenders}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  Page {page} of {tenders.pages}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Area */}
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" p={4}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading tenders...</Typography>
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="h6">Error Loading Tenders</Typography>
          <Typography>{error}</Typography>
          <Button onClick={() => loadTenders()} sx={{ mt: 1 }} variant="contained">
            Retry
          </Button>
        </Alert>
      ) : !tenders ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="h6">No Data Available</Typography>
          <Typography>Please check your connection and try again.</Typography>
          <Button onClick={() => loadTenders()} sx={{ mt: 1 }} variant="contained">
            Retry
          </Button>
        </Alert>
      ) : !tenders.items || tenders.items.length === 0 ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="h6">No Tenders Found</Typography>
          <Typography>Try adjusting your filters or check back later.</Typography>
          <Button onClick={() => {
            setDateFrom('')
            setDateTo('')
            setSearch('')
            setBuyer('')
            setStatus('')
            setAmountMin('')
            setAmountMax('')
            loadTenders()
          }} sx={{ mt: 1 }} variant="outlined">
            Clear Filters
          </Button>
        </Alert>
      ) : (
        <>
          <TableContainer component={Paper} sx={{ maxHeight: '70vh', overflow: 'auto' }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" sx={{ width: 50 }}>
                    <Checkbox
                      indeterminate={
                        tenders?.items.some((item) => {
                          const num = extractTenderNumber(item.tender.all_cells || item.tender.number || '')
                          return selectedTenderNumbers.has(num)
                        }) &&
                        !tenders?.items.every((item) => {
                          const num = extractTenderNumber(item.tender.all_cells || item.tender.number || '')
                          return selectedTenderNumbers.has(num)
                        })
                      }
                      checked={
                        tenders?.items.length > 0 &&
                        tenders.items.every((item) => {
                          const num = extractTenderNumber(item.tender.all_cells || item.tender.number || '')
                          return selectedTenderNumbers.has(num)
                        })
                      }
                      onChange={(e) => {
                        e.stopPropagation()
                        if (e.target.checked) {
                          handleSelectAll()
                        } else {
                          handleDeselectAll()
                        }
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ minWidth: 60 }}>ID</TableCell>
                  <TableCell sx={{ minWidth: 150 }}>Tender Number</TableCell>
                  <TableCell sx={{ minWidth: 120 }}>Type</TableCell>
                  <TableCell sx={{ minWidth: 200 }}>Buyer</TableCell>
                  <TableCell sx={{ minWidth: 250 }}>Category</TableCell>
                  <TableCell align="right" sx={{ minWidth: 120 }}>Amount</TableCell>
                  <TableCell sx={{ minWidth: 110 }}>
                    <TableSortLabel
                      active={sortBy === 'published_date'}
                      direction={sortBy === 'published_date' ? sortOrder : 'asc'}
                      onClick={() => {
                        const isAsc = sortBy === 'published_date' && sortOrder === 'asc'
                        setSortOrder(isAsc ? 'desc' : 'asc')
                        setSortBy('published_date')
                        // Update URL params immediately
                        const newParams = new URLSearchParams(searchParams)
                        newParams.set('sort_by', 'published_date')
                        newParams.set('sort_order', isAsc ? 'desc' : 'asc')
                        setSearchParams(newParams)
                      }}
                    >
                      Published
                    </TableSortLabel>
                  </TableCell>
                  <TableCell sx={{ minWidth: 110 }}>
                    <TableSortLabel
                      active={sortBy === 'deadline_date'}
                      direction={sortBy === 'deadline_date' ? sortOrder : 'asc'}
                      onClick={() => {
                        const isAsc = sortBy === 'deadline_date' && sortOrder === 'asc'
                        setSortOrder(isAsc ? 'desc' : 'asc')
                        setSortBy('deadline_date')
                        // Update URL params immediately
                        const newParams = new URLSearchParams(searchParams)
                        newParams.set('sort_by', 'deadline_date')
                        newParams.set('sort_order', isAsc ? 'desc' : 'asc')
                        setSearchParams(newParams)
                      }}
                    >
                      Deadline
                    </TableSortLabel>
                  </TableCell>
                  <TableCell sx={{ minWidth: 100 }}>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tenders && tenders.items && tenders.items.length > 0 ? (
                  tenders.items.map((item) => {
                    const allCells = item.tender.all_cells || item.tender.buyer || ''
                    // Use structured fields if available, otherwise extract from all_cells (backward compatibility)
                    const buyerName = item.tender.buyer || extractBuyerName(allCells)
                    const category = item.tender.category || extractCategory(allCells)
                    const amount = item.tender.amount ?? extractAmount(allCells)
                    const tenderNum = extractTenderNumber(item.tender.number || allCells)
                    const isSelected = selectedTenderNumbers.has(tenderNum)

                    // Format dates
                    const formatDateDisplay = (dateStr?: string) => {
                      if (!dateStr) return 'N/A'
                      // If already in YYYY-MM-DD format, convert to DD.MM.YYYY for display
                      if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
                        const [year, month, day] = dateStr.split('-')
                        return `${day}.${month}.${year}`
                      }
                      return dateStr
                    }

                    return (
                      <TableRow
                        key={item.id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => handleTenderClick(item)}
                      >
                        <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={isSelected}
                            onChange={(e) => handleToggleSelection(tenderNum, e)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </TableCell>
                        <TableCell>{item.id}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2">{tenderNum}</Typography>
                            {tenderNum && tenderNumbersWithDetails.has(tenderNum.toUpperCase()) && (
                              <Chip
                                label="Detailed"
                                size="small"
                                color="success"
                                sx={{ height: 20, fontSize: '0.65rem' }}
                              />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          {item.tender.tender_type && (
                            <Chip
                              label={item.tender.tender_type}
                              size="small"
                              color="primary"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          )}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 200 }}>
                          <Typography variant="body2" noWrap title={buyerName}>
                            {buyerName}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 250 }}>
                          <Typography variant="body2" noWrap title={category}>
                            {category}
                          </Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                          {formatCurrency(amount)}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                            {formatDateDisplay(item.tender.published_date)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                            {formatDateDisplay(item.tender.deadline_date)}
                          </Typography>
                        </TableCell>
                        <TableCell>{item.tender.status || 'N/A'}</TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={10} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="textSecondary">
                        No tenders found
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {tenders && tenders.pages > 1 && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={tenders.pages}
                page={page}
                onChange={(_, value) => setPage(value)}
              />
            </Box>
          )}

          <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
            <DialogTitle>
              Tender Details
              <IconButton
                onClick={() => setDialogOpen(false)}
                sx={{ position: 'absolute', right: 8, top: 8 }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent>
              {selectedTender && (
                <Box>
                  {/* Loading detailed data */}
                  {loadingDetailed && (
                    <Box display="flex" justifyContent="center" p={2}>
                      <CircularProgress size={24} />
                      <Typography variant="body2" sx={{ ml: 2 }}>
                        Loading detailed data...
                      </Typography>
                    </Box>
                  )}

                  {!loadingDetailed && (
                    <>
                      {/* Header Section - Tender Number and Link */}
                      <Box sx={{ mb: 3, pb: 2, borderBottom: '2px solid', borderColor: 'divider' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Box>
                            <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                              {detailedData?.tender_number || detailedData?.procurement_number || detailedData?.number || extractTenderNumber(selectedTender.tender.number || selectedTender.tender.all_cells || '')}
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                              Tender ID: #{selectedTender.id}
                            </Typography>
                          </Box>
                          {detailedData && (
                            <Chip
                              label="Detailed Data Available"
                              color="success"
                              size="small"
                            />
                          )}
                        </Box>

                        {/* Tender Link */}
                        {(selectedTender.tender.detail_url || selectedTender.tender.tender_id || detailedData?.tender_link) && (
                          <Box sx={{ mt: 1 }}>
                            <Link
                              href={
                                detailedData?.tender_link ||
                                selectedTender.tender.detail_url ||
                                `https://tenders.procurement.gov.ge/public/?go=${selectedTender.tender.tender_id}&lang=ge`
                              }
                              target="_blank"
                              rel="noopener noreferrer"
                              sx={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                wordBreak: 'break-all',
                                color: 'primary.main',
                                textDecoration: 'none',
                                '&:hover': { textDecoration: 'underline' }
                              }}
                            >
                              <Typography variant="body2">
                                🔗 {detailedData?.tender_link ||
                                  selectedTender.tender.detail_url ||
                                  `https://tenders.procurement.gov.ge/public/?go=${selectedTender.tender.tender_id}&lang=ge`}
                              </Typography>
                            </Link>
                          </Box>
                        )}

                        {/* Find Similar Tenders Button */}
                        {((detailedData?.buyer && detailedData?.category) ||
                          (selectedTender.tender.buyer && selectedTender.tender.category)) && (
                            <Box sx={{ mt: 2 }}>
                              <Button
                                variant="outlined"
                                color="primary"
                                onClick={handleFindSimilar}
                                disabled={loadingSimilar}
                                startIcon={loadingSimilar ? <CircularProgress size={20} /> : <SearchIcon />}
                                fullWidth
                              >
                                {loadingSimilar ? 'Searching...' : 'Find Similar Tenders (Same Buyer & Category)'}
                              </Button>
                            </Box>
                          )}
                      </Box>

                      {/* Debug Info - Collapsible */}
                      {detailedData && (
                        <Accordion
                          expanded={debugExpanded}
                          onChange={() => setDebugExpanded(!debugExpanded)}
                          sx={{ mb: 2 }}
                        >
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography variant="caption" color="textSecondary">
                              🔍 Debug Info
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>
                              ✅ Detailed data loaded: {detailedData.tender_number || detailedData.procurement_number || detailedData.number}
                            </Typography>
                            <Typography variant="caption" sx={{ display: 'block' }}>
                              Tabs: {detailedData.tabs_data ? Object.keys(detailedData.tabs_data).length : 0} |
                              Full text: {detailedData.full_text ? detailedData.full_text.length.toLocaleString() : 0} chars |
                              Basic info fields: {detailedData.basic_info ? Object.keys(detailedData.basic_info).length : 0}
                            </Typography>
                          </AccordionDetails>
                        </Accordion>
                      )}

                      {/* Expand/Collapse All Button */}
                      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
                        <Button
                          size="small"
                          onClick={() => {
                            const allExpanded = Object.values(expandedSections).every(v => v) && debugExpanded
                            const newState = !allExpanded
                            setDebugExpanded(newState)
                            setExpandedSections({
                              debug: newState,
                              basicInfo: newState,
                              dates: newState,
                              financial: newState,
                              requirements: newState,
                              description: newState,
                              specifications: newState,
                              documents: newState,
                              timeline: newState,
                              contacts: newState,
                              terms: newState,
                              additional: newState,
                              tabs: newState,
                              fullText: newState,
                            })
                          }}
                        >
                          {Object.values(expandedSections).every(v => v) && debugExpanded ? 'Collapse All' : 'Expand All'}
                        </Button>
                      </Box>
                    </>
                  )}

                  {/* Basic Info from Detailed Data - New Structure */}
                  {(detailedData?.tender_type || detailedData?.buyer || detailedData?.category || detailedData?.status || detailedData?.title) && (
                    <Accordion
                      expanded={expandedSections.basicInfo}
                      onChange={() => setExpandedSections({ ...expandedSections, basicInfo: !expandedSections.basicInfo })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                          📋 Basic Information
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Grid container spacing={2}>
                          {detailedData?.title && (
                            <Grid item xs={12}>
                              <Typography variant="body2">
                                <strong>Title:</strong> {detailedData.title}
                              </Typography>
                            </Grid>
                          )}
                          {detailedData?.tender_type && (
                            <Grid item xs={12} md={6}>
                              <Typography variant="body2">
                                <strong>Tender Type:</strong> {detailedData.tender_type}
                              </Typography>
                            </Grid>
                          )}
                          {detailedData?.buyer && (
                            <Grid item xs={12}>
                              <Typography variant="body2">
                                <strong>Buyer:</strong> {detailedData.buyer}
                              </Typography>
                            </Grid>
                          )}
                          {detailedData?.category && (
                            <Grid item xs={12}>
                              <Typography variant="body2">
                                <strong>Category:</strong> {detailedData.category}
                              </Typography>
                            </Grid>
                          )}
                          {detailedData?.status && (
                            <Grid item xs={12} md={6}>
                              <Typography variant="body2">
                                <strong>Status:</strong> {detailedData.status}
                              </Typography>
                            </Grid>
                          )}
                          {detailedData?.classifier_codes && Array.isArray(detailedData.classifier_codes) && detailedData.classifier_codes.length > 0 && (
                            <Grid item xs={12}>
                              <Typography variant="body2" gutterBottom>
                                <strong>Classifier Codes:</strong>
                              </Typography>
                              <Box component="ul" sx={{ pl: 2, m: 0 }}>
                                {detailedData.classifier_codes.map((code: string, idx: number) => (
                                  <li key={idx}>
                                    <Typography variant="body2">{code}</Typography>
                                  </li>
                                ))}
                              </Box>
                            </Grid>
                          )}
                          {detailedData?.quantity_or_volume && (
                            <Grid item xs={12}>
                              <Typography variant="body2">
                                <strong>Quantity/Volume:</strong> {detailedData.quantity_or_volume}
                              </Typography>
                            </Grid>
                          )}
                        </Grid>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Dates Section - New Structure */}
                  {(detailedData?.published_date ||
                    detailedData?.deadline_date ||
                    detailedData?.entry_date ||
                    detailedData?.last_modification ||
                    detailedData?.delivery_terms?.delivery_deadline) && (
                      <Accordion
                        expanded={expandedSections.dates}
                        onChange={() => setExpandedSections({ ...expandedSections, dates: !expandedSections.dates })}
                        sx={{ mb: 1 }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                            📅 Dates & Deadlines
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Grid container spacing={1}>
                            {detailedData.published_date && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Published Date:</strong> {detailedData.published_date}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.deadline_date && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Deadline Date:</strong> {detailedData.deadline_date}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.entry_date && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Entry Date:</strong> {detailedData.entry_date}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.last_modification && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Last Modification:</strong> {detailedData.last_modification}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.delivery_terms?.delivery_deadline && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Delivery Deadline:</strong> {detailedData.delivery_terms.delivery_deadline}
                                </Typography>
                              </Grid>
                            )}
                          </Grid>
                        </AccordionDetails>
                      </Accordion>
                    )}

                  {/* Financial Section - New Structure */}
                  {(detailedData?.estimated_value ||
                    detailedData?.price_reduction_step ||
                    detailedData?.guarantee?.amount ||
                    detailedData?.guarantee?.validity_days ||
                    detailedData?.vat_included !== undefined) && (
                      <Accordion
                        expanded={expandedSections.financial}
                        onChange={() => setExpandedSections({ ...expandedSections, financial: !expandedSections.financial })}
                        sx={{ mb: 1 }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                            💰 Financial Information
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Grid container spacing={1}>
                            {detailedData.estimated_value && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Estimated Value:</strong> {detailedData.estimated_value} {detailedData.currency || 'GEL'}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.vat_included !== undefined && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>VAT Included:</strong> {detailedData.vat_included ? 'Yes' : 'No'}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.price_reduction_step && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Price Reduction Step:</strong> {detailedData.price_reduction_step} {detailedData.currency || 'GEL'}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.guarantee?.amount && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Guarantee Amount:</strong> {detailedData.guarantee.amount} {detailedData.currency || 'GEL'}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.guarantee?.validity_days && (
                              <Grid item xs={12} md={6}>
                                <Typography variant="body2">
                                  <strong>Guarantee Validity:</strong> {detailedData.guarantee.validity_days} days
                                </Typography>
                              </Grid>
                            )}
                          </Grid>
                        </AccordionDetails>
                      </Accordion>
                    )}

                  {/* Requirements Section - New Structure */}
                  {(detailedData?.proposal_submission_requirement ||
                    detailedData?.additional_information ||
                    detailedData?.additional_requirements) && (
                      <Accordion
                        expanded={expandedSections.requirements}
                        onChange={() => setExpandedSections({ ...expandedSections, requirements: !expandedSections.requirements })}
                        sx={{ mb: 1 }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                            📝 Requirements & Additional Information
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Grid container spacing={1}>
                            {detailedData.proposal_submission_requirement && (
                              <Grid item xs={12}>
                                <Typography variant="body2">
                                  <strong>Proposal Submission Requirement:</strong> {detailedData.proposal_submission_requirement}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.additional_information && (
                              <Grid item xs={12}>
                                <Typography variant="body2">
                                  <strong>Additional Information:</strong> {detailedData.additional_information}
                                </Typography>
                              </Grid>
                            )}
                            {detailedData.additional_requirements && (
                              <Grid item xs={12}>
                                <Typography variant="body2" gutterBottom>
                                  <strong>Additional Requirements:</strong>
                                </Typography>
                                {detailedData.additional_requirements.sample_required && (
                                  <Typography variant="body2">• Sample Required</Typography>
                                )}
                                {detailedData.additional_requirements.warranty_required && (
                                  <Typography variant="body2">• Warranty Required: {detailedData.additional_requirements.warranty_details}</Typography>
                                )}
                                {detailedData.additional_requirements.pricing_adequacy_required && (
                                  <Typography variant="body2">• Pricing Adequacy Required</Typography>
                                )}
                              </Grid>
                            )}
                          </Grid>
                        </AccordionDetails>
                      </Accordion>
                    )}

                  {/* Description */}
                  {detailedData?.description && detailedData.description.trim() && (
                    <Accordion
                      expanded={expandedSections.description}
                      onChange={() => setExpandedSections({ ...expandedSections, description: !expandedSections.description })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          📄 Description
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {detailedData.description}
                        </Typography>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Specifications - New Structure */}
                  {(detailedData?.specifications || detailedData?.technical_specifications?.raw_text) && (
                    <Accordion
                      expanded={expandedSections.specifications}
                      onChange={() => setExpandedSections({ ...expandedSections, specifications: !expandedSections.specifications })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          🔧 Technical Specifications
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography
                          variant="body2"
                          component="pre"
                          sx={{
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: '0.875rem',
                            lineHeight: 1.6,
                            bgcolor: 'grey.50',
                            p: 2,
                            borderRadius: 1
                          }}
                        >
                          {detailedData.technical_specifications?.raw_text || detailedData.specifications}
                        </Typography>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Documents */}
                  {detailedData?.documents && detailedData.documents.length > 0 && (
                    <Accordion
                      expanded={expandedSections.documents}
                      onChange={() => setExpandedSections({ ...expandedSections, documents: !expandedSections.documents })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          📎 Documents ({detailedData.documents.length})
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Stack spacing={2}>
                          {detailedData.documents.map((doc, idx) => {
                            const isPdf = doc.type?.toLowerCase() === 'pdf' || doc.url?.toLowerCase().includes('.pdf')
                            const isExcel = doc.type?.toLowerCase() === 'xls' || doc.type?.toLowerCase() === 'xlsx' ||
                              doc.url?.toLowerCase().includes('.xls')
                            const isDoc = doc.type?.toLowerCase() === 'doc' || doc.type?.toLowerCase() === 'docx' ||
                              doc.url?.toLowerCase().includes('.doc')
                            const canViewOnline = isPdf || isExcel

                            // Get icon for file type
                            const getFileIcon = () => {
                              if (isPdf) return <PictureAsPdfIcon sx={{ color: 'error.main' }} />
                              if (isExcel) return <TableChartIcon sx={{ color: 'success.main' }} />
                              if (isDoc) return <DescriptionIcon sx={{ color: 'info.main' }} />
                              return <InsertDriveFileIcon />
                            }

                            return (
                              <Box
                                key={idx}
                                sx={{
                                  p: 2,
                                  border: '1px solid',
                                  borderColor: 'divider',
                                  borderRadius: 1,
                                  bgcolor: 'grey.50',
                                  '&:hover': {
                                    bgcolor: 'grey.100',
                                    borderColor: 'primary.main'
                                  }
                                }}
                              >
                                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 1.5 }}>
                                  <Box sx={{ mt: 0.5 }}>
                                    {getFileIcon()}
                                  </Box>
                                  <Box sx={{ flex: 1 }}>
                                    <Typography variant="body1" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                                      {doc.name || `Document ${idx + 1}`}
                                    </Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                      <Chip
                                        label={doc.type?.toUpperCase() || 'FILE'}
                                        size="small"
                                        color={isPdf ? 'error' : isExcel ? 'success' : isDoc ? 'info' : 'default'}
                                      />
                                      {canViewOnline && (
                                        <Chip
                                          label="Viewable Online"
                                          size="small"
                                          variant="outlined"
                                          color="primary"
                                        />
                                      )}
                                    </Box>
                                    <Typography
                                      variant="caption"
                                      color="textSecondary"
                                      sx={{
                                        display: 'block',
                                        wordBreak: 'break-all',
                                        fontFamily: 'monospace',
                                        fontSize: '0.7rem'
                                      }}
                                    >
                                      {doc.url}
                                    </Typography>
                                  </Box>
                                </Box>
                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                  {canViewOnline && (
                                    <Button
                                      size="small"
                                      variant="outlined"
                                      component="a"
                                      href={doc.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      startIcon={<VisibilityIcon />}
                                      sx={{ textTransform: 'none' }}
                                    >
                                      View Online
                                    </Button>
                                  )}
                                  <Button
                                    size="small"
                                    variant="contained"
                                    component="a"
                                    href={doc.url}
                                    download
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    startIcon={<DownloadIcon />}
                                    sx={{ textTransform: 'none' }}
                                  >
                                    Download
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={() => {
                                      navigator.clipboard.writeText(doc.url)
                                      // Could add a snackbar notification here
                                    }}
                                    startIcon={<ContentCopyIcon />}
                                    sx={{ textTransform: 'none' }}
                                  >
                                    Copy Link
                                  </Button>
                                </Box>
                              </Box>
                            )
                          })}
                        </Stack>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Bids Section - NEW */}
                  {detailedData?.bids && detailedData.bids.length > 0 && (
                    <Accordion
                      expanded={expandedSections.bids || false}
                      onChange={() => setExpandedSections({ ...expandedSections, bids: !(expandedSections.bids || false) })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          💼 Bids ({detailedData.bids.length} bidders)
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <TableContainer component={Paper} sx={{ mb: 2 }}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell><strong>Supplier</strong></TableCell>
                                <TableCell align="right"><strong>First Offer</strong></TableCell>
                                <TableCell align="right"><strong>Last Offer</strong></TableCell>
                                <TableCell><strong>First Date</strong></TableCell>
                                <TableCell><strong>Last Date</strong></TableCell>
                                <TableCell align="right"><strong>Discount</strong></TableCell>
                                <TableCell><strong>Rounds</strong></TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {detailedData.bids.map((bid: any, idx: number) => {
                                const firstAmount = parseFloat(bid.first_offer_amount || '0')
                                const lastAmount = parseFloat(bid.last_offer_amount || '0')
                                const estimatedValue = parseFloat(detailedData.estimated_value || '0')

                                // Calculate discount from estimated_value to last_offer_amount
                                let discount = '0.00'
                                if (estimatedValue > 0 && lastAmount > 0) {
                                  const discountAmount = estimatedValue - lastAmount
                                  const discountPercent = (discountAmount / estimatedValue) * 100
                                  discount = discountPercent.toFixed(2)
                                } else if (firstAmount > 0 && lastAmount > 0) {
                                  // Fallback: if no estimated_value, use first_offer as before
                                  discount = ((firstAmount - lastAmount) / firstAmount * 100).toFixed(2)
                                }

                                return (
                                  <TableRow key={idx} sx={{ bgcolor: bid.supplier === detailedData.winner?.supplier ? 'success.light' : 'inherit' }}>
                                    <TableCell>{bid.supplier || 'N/A'}</TableCell>
                                    <TableCell align="right">{firstAmount.toLocaleString('ka-GE')} GEL</TableCell>
                                    <TableCell align="right">{lastAmount.toLocaleString('ka-GE')} GEL</TableCell>
                                    <TableCell>{bid.first_offer_time || 'N/A'}</TableCell>
                                    <TableCell>{bid.last_offer_time || 'N/A'}</TableCell>
                                    <TableCell align="right">{discount}%</TableCell>
                                    <TableCell>{bid.rounds?.length || 0}</TableCell>
                                  </TableRow>
                                )
                              })}
                            </TableBody>
                          </Table>
                        </TableContainer>
                        {detailedData.winner?.supplier && (
                          <Alert severity="success" sx={{ mb: 1 }}>
                            <Typography variant="body2">
                              <strong>Winner:</strong> {detailedData.winner.supplier} - {parseFloat(detailedData.winner.amount || '0').toLocaleString('ka-GE')} GEL
                              {detailedData.winner.award_date && ` (Awarded: ${detailedData.winner.award_date})`}
                            </Typography>
                          </Alert>
                        )}
                        {detailedData.lowest_bidder?.supplier && (
                          <Alert severity="info">
                            <Typography variant="body2">
                              <strong>Lowest Bidder:</strong> {detailedData.lowest_bidder.supplier} - {parseFloat(detailedData.lowest_bidder.amount || '0').toLocaleString('ka-GE')} GEL
                            </Typography>
                          </Alert>
                        )}
                        {detailedData.bidders_count !== undefined && (
                          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                            Total Bidders: {detailedData.bidders_count}
                          </Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Contracts Section - NEW */}
                  {detailedData?.contracts && detailedData.contracts.length > 0 && (
                    <Accordion
                      expanded={expandedSections.contracts || false}
                      onChange={() => setExpandedSections({ ...expandedSections, contracts: !(expandedSections.contracts || false) })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          📝 Contracts ({detailedData.contracts.length})
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Stack spacing={2}>
                          {detailedData.contracts.map((contract: any, idx: number) => (
                            <Card key={idx} variant="outlined">
                              <CardContent>
                                <Typography variant="body1" gutterBottom>
                                  <strong>Contract ID:</strong> {contract.contract_id || 'N/A'}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Supplier:</strong> {contract.supplier || 'N/A'}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Amount:</strong> {parseFloat(contract.amount || '0').toLocaleString('ka-GE')} GEL
                                </Typography>
                                {contract.signing_date && (
                                  <Typography variant="body2">
                                    <strong>Signing Date:</strong> {contract.signing_date}
                                  </Typography>
                                )}
                                {contract.contract_url && (
                                  <Button
                                    size="small"
                                    component="a"
                                    href={contract.contract_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    sx={{ mt: 1 }}
                                  >
                                    View Contract
                                  </Button>
                                )}
                              </CardContent>
                            </Card>
                          ))}
                        </Stack>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Timeline */}
                  {detailedData?.timeline && detailedData.timeline.length > 0 && (
                    <Accordion
                      expanded={expandedSections.timeline}
                      onChange={() => setExpandedSections({ ...expandedSections, timeline: !expandedSections.timeline })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          📅 Timeline
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Stack spacing={1}>
                          {detailedData.timeline.map((event: any, idx: number) => (
                            <Typography key={idx} variant="body2">
                              <strong>{event.date || event.time}:</strong> {event.event || JSON.stringify(event)}
                            </Typography>
                          ))}
                        </Stack>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Contacts */}
                  {detailedData?.contacts && Object.keys(detailedData.contacts).length > 0 && (
                    <Accordion
                      expanded={expandedSections.contacts}
                      onChange={() => setExpandedSections({ ...expandedSections, contacts: !expandedSections.contacts })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          📞 Contact Information
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        {detailedData.contacts.phone && (
                          <Typography variant="body2">Phone: {detailedData.contacts.phone}</Typography>
                        )}
                        {detailedData.contacts.email && (
                          <Typography variant="body2">Email: {detailedData.contacts.email}</Typography>
                        )}
                        {detailedData.contacts.address && (
                          <Typography variant="body2">Address: {detailedData.contacts.address}</Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Terms */}
                  {detailedData?.terms && detailedData.terms.trim() && (
                    <Accordion
                      expanded={expandedSections.terms}
                      onChange={() => setExpandedSections({ ...expandedSections, terms: !expandedSections.terms })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          📋 Terms
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {detailedData.terms}
                        </Typography>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* All Sections (structured data from parser) */}
                  {detailedData?.all_sections && Object.keys(detailedData.all_sections).length > 0 && (
                    <Accordion
                      expanded={expandedSections.additional}
                      onChange={() => setExpandedSections({ ...expandedSections, additional: !expandedSections.additional })}
                      sx={{ mb: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                          ℹ️ Additional Information
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        {Object.entries(detailedData.all_sections).map(([key, value]) => (
                          <Box key={key} sx={{ mb: 1.5 }}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                              {key}:
                            </Typography>
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', pl: 2 }}>
                              {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                            </Typography>
                          </Box>
                        ))}
                      </AccordionDetails>
                    </Accordion>
                  )}

                  {/* Tabs Data - Show only non-duplicated content */}
                  {(() => {
                    const deduplicated = deduplicateContent(detailedData)
                    return deduplicated?.tabs_data && Object.keys(deduplicated.tabs_data).length > 0 && (
                      <Accordion
                        expanded={expandedSections.tabs}
                        onChange={() => setExpandedSections({ ...expandedSections, tabs: !expandedSections.tabs })}
                        sx={{ mb: 1 }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                            📑 Additional Tab Content ({Object.keys(deduplicated.tabs_data).length} tabs)
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 2 }}>
                            Showing only content not already displayed in Basic Information
                          </Typography>
                          {Object.entries(deduplicated.tabs_data).map(([tabName, tabContent]) => {
                            const textContent = typeof tabContent === 'object' ? (tabContent.text || tabContent.html || '') : String(tabContent || '');
                            const contentLength = textContent.length;
                            return (
                              <Box key={tabName} sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1, border: '1px solid', borderColor: 'grey.300' }}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, color: 'primary.dark' }}>
                                  {tabName} ({contentLength.toLocaleString()} chars)
                                </Typography>
                                <Typography
                                  variant="body2"
                                  component="pre"
                                  sx={{
                                    whiteSpace: 'pre-wrap',
                                    maxHeight: '500px',
                                    overflow: 'auto',
                                    fontFamily: 'monospace',
                                    fontSize: '0.875rem',
                                    lineHeight: 1.6
                                  }}
                                >
                                  {textContent || 'No content available'}
                                </Typography>
                              </Box>
                            );
                          })}
                        </AccordionDetails>
                      </Accordion>
                    )
                  })()}

                  {/* Full Text - Show only non-duplicated content */}
                  {(() => {
                    const deduplicated = deduplicateContent(detailedData)
                    return deduplicated?.full_text && deduplicated.full_text.trim() && (
                      <Accordion
                        expanded={expandedSections.fullText}
                        onChange={() => setExpandedSections({ ...expandedSections, fullText: !expandedSections.fullText })}
                        sx={{ mb: 1 }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                            📄 Additional Scraped Content ({deduplicated.full_text.length.toLocaleString()} chars)
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 2 }}>
                            Showing only content not already displayed in Basic Information
                          </Typography>
                          <Typography
                            variant="body2"
                            component="pre"
                            sx={{
                              whiteSpace: 'pre-wrap',
                              maxHeight: '600px',
                              overflow: 'auto',
                              p: 2,
                              bgcolor: 'grey.50',
                              borderRadius: 1,
                              fontSize: '0.875rem',
                              fontFamily: 'monospace',
                              lineHeight: 1.6,
                              border: '1px solid',
                              borderColor: 'grey.300'
                            }}
                          >
                            {deduplicated.full_text}
                          </Typography>
                        </AccordionDetails>
                      </Accordion>
                    )
                  })()}

                  {/* Fallback to basic text if no detailed data */}
                  {!detailedData && !loadingDetailed && (
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', mt: 2 }}>
                      {selectedTender.tender.all_cells || selectedTender.tender.buyer}
                    </Typography>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              {detailedData && !loadingDetailed && (
                <Button
                  color="error"
                  variant="outlined"
                  onClick={() => setDeleteConfirmOpen(true)}
                  disabled={deleting}
                >
                  Delete Detailed Data
                </Button>
              )}
              {selectedTender?.tender.detail_url && (
                <Button
                  component="a"
                  href={selectedTender.tender.detail_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="outlined"
                >
                  View Online
                </Button>
              )}
              <Button onClick={() => setDialogOpen(false)}>Close</Button>
            </DialogActions>
          </Dialog>

          {/* Delete Confirmation Dialog */}
          <Dialog open={deleteConfirmOpen} onClose={() => !deleting && setDeleteConfirmOpen(false)}>
            <DialogTitle>Delete Detailed Data?</DialogTitle>
            <DialogContent>
              <Typography>
                Are you sure you want to delete detailed data for tender{' '}
                <strong>{detailedData?.tender_number || detailedData?.procurement_number || detailedData?.number}</strong>?
                <br />
                <br />
                This action cannot be undone. You will need to scrape the data again to restore it.
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDeleteConfirmOpen(false)} disabled={deleting}>
                Cancel
              </Button>
              <Button
                onClick={handleDeleteDetailedData}
                color="error"
                variant="contained"
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </Button>
            </DialogActions>
          </Dialog>
        </>
      )}

      {/* Group Tenders Dialog */}
      <Dialog
        open={selectedGroup !== null}
        onClose={() => setSelectedGroup(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {selectedGroup && (
            <>
              Tenders in {groupBy === 'category' ? 'Category' : 'Buyer'}: {selectedGroup.name}
              <Typography variant="body2" color="textSecondary">
                {selectedGroup.tenders.length} tender{selectedGroup.tenders.length !== 1 ? 's' : ''}
              </Typography>
            </>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedGroup && selectedGroup.tenders.map((tender, index) => (
            <Card key={index} sx={{ mb: 2, cursor: 'pointer' }} onClick={() => {
              handleTenderClick(tender)
              setSelectedGroup(null)
            }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Box flex={1}>
                    <Typography variant="h6" gutterBottom>
                      {tender.tender.number || extractTenderNumber(tender.tender.all_cells)}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" paragraph>
                      {tender.tender.buyer}
                    </Typography>
                    {tender.tender.category && (
                      <Typography variant="body2" color="primary">
                        📁 {tender.tender.category}
                      </Typography>
                    )}
                  </Box>
                  <Box textAlign="right">
                    {tender.tender.amount && (
                      <Typography variant="h6" color="primary">
                        {formatCurrency(tender.tender.amount)}
                      </Typography>
                    )}
                    <Typography variant="caption" color="textSecondary">
                      {tender.tender.status}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedGroup(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Similar Tenders Dialog */}
      <Dialog
        open={similarDialogOpen}
        onClose={() => setSimilarDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Similar Tenders
          <IconButton
            onClick={() => setSimilarDialogOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {similarTenders && (
            <>
              <Box sx={{ mb: 3, p: 2, bgcolor: 'background.paper', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
                <Typography variant="h6" gutterBottom>
                  Found {similarTenders.total} similar tender{similarTenders.total !== 1 ? 's' : ''}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  <strong>Buyer:</strong> {detailedData?.buyer || selectedTender?.tender.buyer}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  <strong>Category:</strong> {detailedData?.category || selectedTender?.tender.category}
                </Typography>
              </Box>

              {similarTenders.total === 0 ? (
                <Alert severity="info">
                  No similar tenders found with the same buyer and category.
                </Alert>
              ) : (
                <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Tender Number</strong></TableCell>
                        <TableCell><strong>Published Date</strong></TableCell>
                        <TableCell><strong>Deadline</strong></TableCell>
                        <TableCell align="right"><strong>Amount</strong></TableCell>
                        <TableCell><strong>Status</strong></TableCell>
                        <TableCell align="center"><strong>Actions</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {similarTenders.items.map((item) => (
                        <TableRow
                          key={item.id}
                          hover
                          sx={{ '&:hover': { bgcolor: 'action.hover' } }}
                        >
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {item.tender.number || extractTenderNumber(item.tender.all_cells)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {item.tender.published_date || 'N/A'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {item.tender.deadline_date || 'N/A'}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" sx={{ fontWeight: item.tender.amount ? 'bold' : 'normal' }}>
                              {formatCurrency(item.tender.amount)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={item.tender.status || 'Unknown'}
                              size="small"
                              color={
                                item.tender.status?.toLowerCase().includes('active') ? 'success' :
                                  item.tender.status?.toLowerCase().includes('completed') ? 'default' :
                                    'warning'
                              }
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<VisibilityIcon />}
                              onClick={() => {
                                setSimilarDialogOpen(false)
                                handleTenderClick(item)
                              }}
                            >
                              View
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSimilarDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Deep Search Dialog */}
      <Dialog
        open={deepSearchOpen}
        onClose={() => setDeepSearchOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Search in Detailed Data</Typography>
            <IconButton onClick={() => setDeepSearchOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 3 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={10}>
                <TextField
                  fullWidth
                  label="Search Text"
                  placeholder="Enter text to search across all fields..."
                  value={deepSearchQuery}
                  onChange={(e) => setDeepSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleDeepSearch()}
                  autoFocus
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleDeepSearch}
                  disabled={searchingDeep || !deepSearchQuery.trim()}
                  startIcon={searchingDeep ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                  sx={{ height: '56px' }}
                >
                  Search
                </Button>
              </Grid>
            </Grid>
          </Box>

          {deepSearchResults.length > 0 ? (
            <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tender Number</TableCell>
                    <TableCell>Buyer</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {deepSearchResults.map((tender) => (
                    <TableRow key={tender.tender_number || tender.procurement_number || tender.number} hover>
                      <TableCell>
                        <Button
                          size="small"
                          sx={{
                            fontFamily: 'monospace',
                            fontWeight: 'bold',
                            textTransform: 'none',
                            p: 0,
                            minWidth: 'auto',
                            justifyContent: 'flex-start',
                            textAlign: 'left'
                          }}
                          onClick={() => {
                            // Convert DetailedTender to TenderResponse structure
                            const tenderResponse: any = {
                              id: 0, // Dummy ID
                              tender: {
                                number: tender.tender_number || tender.procurement_number || tender.number,
                                buyer: tender.buyer,
                                category: tender.category,
                                status: tender.status,
                                amount: tender.estimated_value ? parseFloat(tender.estimated_value) : 0,
                                published_date: tender.published_date,
                                deadline_date: tender.deadline_date,
                                detail_url: tender.detail_url,
                                all_cells: '', // Fallback
                                tender_id: tender.tender_id
                              }
                            }
                            handleTenderClick(tenderResponse)
                            // Keep search dialog open
                          }}
                        >
                          {tender.tender_number || tender.procurement_number || tender.number}
                        </Button>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 250 }} title={tender.buyer}>
                          {tender.buyer}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 200 }} title={tender.category}>
                          {tender.category}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={tender.status}
                          size="small"
                          color={tender.status && tender.status.includes('გამოცხადებულია') ? 'success' : 'default'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">
                        {tender.estimated_value ? (
                          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                            {formatCurrency(Number(tender.estimated_value))}
                          </Typography>
                        ) : '-'}
                      </TableCell>
                      <TableCell align="center">
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            setTenderNumber(tender.tender_number || tender.procurement_number || tender.number || '');
                            handleSearch();
                            setDeepSearchOpen(false);
                          }}
                        >
                          Filter
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <Typography color="textSecondary">
                {searchingDeep ? 'Searching...' : deepSearchResults.length === 0 && deepSearchQuery ? 'No matches found' : 'Enter text to search'}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeepSearchOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box >
  )
}

