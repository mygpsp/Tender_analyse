import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Tender {
  number: string
  buyer: string
  supplier: string
  status: string
  participants_count?: number  // Number of participants (მონაწილეთა რაოდენობა)
  amount?: number  // Tender amount in GEL
  published_date?: string  // Publication date (YYYY-MM-DD)
  deadline_date?: string  // Proposal deadline (YYYY-MM-DD)
  category?: string  // Full category description (CODE-DESCRIPTION)
  category_code?: string  // CPV category code (8 digits)
  tender_type?: string  // Tender type (GEO, NAT, CON, etc.)
  all_cells: string
  scraped_at?: number
  date_window?: {
    from: string
    to: string
  }
  extraction_method?: string
  tender_id?: string
  detail_url?: string
}

export interface TenderResponse {
  id: number
  tender: Tender
}

export interface TenderListResponse {
  items: TenderResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AnalyticsSummary {
  total_tenders: number
  total_amount?: number
  avg_amount?: number
  unique_buyers: number
  date_range?: {
    from: string
    to: string
  }
}

export interface BuyerStats {
  name: string
  tender_count: number
  total_amount?: number
}

export interface WinnerStats {
  name: string
  tender_count: number
  total_amount?: number
  avg_amount?: number
}

export interface CategoryStats {
  category: string
  tender_count: number
  total_amount?: number
}

export interface TimelinePoint {
  date: string
  count: number
  total_amount?: number
}

// API functions
export const tendersApi = {
  list: async (params?: {
    page?: number
    page_size?: number
    buyer?: string
    status?: string
    date_from?: string
    date_to?: string
    filter_by_published_date?: boolean
    filter_by_deadline_date?: boolean
    search?: string
    amount_min?: number
    amount_max?: number
    tender_number?: string
    has_detailed_data?: boolean
    sort_by?: string
    sort_order?: string
  }): Promise<TenderListResponse> => {
    const response = await api.get('/api/tenders', { params })
    return response.data
  },

  get: async (id: number): Promise<TenderResponse> => {
    const response = await api.get(`/api/tenders/${id}`)
    return response.data
  },

  getSimilar: async (id: number, limit?: number): Promise<TenderListResponse> => {
    const response = await api.get(`/api/tenders/${id}/similar`, {
      params: { limit }
    })
    return response.data
  },
}

// Detailed Tender Interfaces - New Structure
export interface DetailedTender {
  // Core identification
  tender_id?: string
  procurement_number?: string
  number?: string  // Backward compatibility
  detail_url?: string
  tender_type?: string
  status?: string

  // Basic info
  title?: string
  description?: string
  additional_information?: string
  category?: string
  category_code?: string
  classifier_codes?: string[]

  // Buyer
  buyer?: string
  buyer_contacts?: {
    name?: string
    phone?: string
    email?: string
  }

  // Dates
  published_date?: string
  deadline_date?: string
  entry_date?: string
  last_modification?: string

  // Financial
  estimated_value?: string
  currency?: string
  vat_included?: boolean
  proposal_submission_requirement?: string
  quantity_or_volume?: string

  // Delivery terms
  delivery_terms?: {
    delivery_deadline?: string
    delivery_start_date?: string
    delivery_end_date?: string
    delivery_type?: string
    delivery_address?: string
  }

  // Price and guarantee
  price_reduction_step?: string
  guarantee?: {
    required?: boolean
    amount?: string
    validity_days?: string
  }

  // Payment terms
  payment_terms?: {
    prepayment_allowed?: boolean
    prepayment_conditions?: string
    final_payment_terms?: string
    final_payment_deadline_days?: string
  }

  // Documents
  documents?: Array<{
    name: string
    url: string
    type: string
  }>

  // Tabs data
  tabs_data?: {
    documentation?: {
      text: string
      documents_count: number
      raw_html: string
    }
    offers?: {
      text: string
      documents_count: number
      raw_html: string
    }
    results?: {
      text: string
      documents_count: number
      raw_html: string
    }
  }

  // Technical specifications
  technical_specifications?: {
    raw_text: string
    items: any[]
  }

  // Additional requirements
  additional_requirements?: {
    sample_required?: boolean
    sample_deadline?: string
    sample_address?: string
    pricing_adequacy_required?: boolean
    pricing_adequacy_terms?: string
    warranty_required?: boolean
    warranty_details?: string
    no_alternative_offer?: boolean
  }

  // Bids
  bids?: Array<{
    supplier: string
    first_offer_amount: string
    last_offer_amount: string
    first_offer_time: string
    last_offer_time: string
    rounds?: Array<{
      round_number: string
      time_start: string
      time_end: string
      amount: string
    }>
  }>

  // Winner and lowest bidder
  winner?: {
    supplier: string
    amount: string
    award_date: string
  }
  lowest_bidder?: {
    supplier: string
    amount: string
  }
  bidders_count?: number

  // Contracts
  contracts?: Array<{
    contract_id: string
    supplier: string
    amount: string
    signing_date: string
    contract_url: string
  }>

  // Timeline, deadlines, contacts
  timeline?: Array<any>
  deadlines?: Record<string, any>
  contacts?: Record<string, any>

  // Raw HTML tables
  raw_html_tables?: {
    documentation_tab?: string
    offers_tab?: string
    results_tab?: string
  }

  // Backward compatibility fields
  all_cells?: string
  extraction_method?: string
  scraped_at?: number

  // Old fields (for backward compatibility)
  tender_number?: string
  tender_link?: string
  full_text?: string
  html_content?: string
  basic_info?: any
  specifications?: string
  terms?: string
  structured_sections?: Record<string, string>
}

export interface DetailedTenderListResponse {
  items: DetailedTender[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export const detailedTendersApi = {
  list: async (params?: {
    tender_number?: string
    limit?: number
    offset?: number
  }): Promise<DetailedTenderListResponse> => {
    const response = await api.get('/api/detailed-tenders/list', { params })
    return response.data
  },
  getByTenderNumber: async (tenderNumber: string): Promise<DetailedTender> => {
    const response = await api.get(`/api/detailed-tenders/${tenderNumber}`)
    return response.data
  },

  search: async (query: string): Promise<DetailedTender[]> => {
    const response = await api.get('/api/detailed-tenders/search', {
      params: { query }
    })
    return response.data.items
  },

  reload: async (): Promise<{ status: string; message: string; count: number }> => {
    const response = await api.post('/api/detailed-tenders/reload')
    return response.data
  },
  getTenderNumbers: async (): Promise<{ tender_numbers: string[]; count: number }> => {
    const response = await api.get('/api/detailed-tenders/tender-numbers')
    return response.data
  },
  delete: async (tender_number: string): Promise<{ status: string; message: string; tender_number: string }> => {
    const response = await api.delete(`/api/detailed-tenders/${tender_number}`)
    return response.data
  },

  browse: async (params?: {
    offset?: number
    limit?: number
  }): Promise<{
    items: DetailedTender[]
    total: number
    offset: number
    limit: number
    has_previous: boolean
    has_next: boolean
  }> => {
    const response = await api.get('/api/detailed-tenders/browse', { params })
    return response.data
  },
}

export const analyticsApi = {
  summary: async (params?: {
    buyer?: string
    status?: string
    date_from?: string
    date_to?: string
    filter_by_published_date?: boolean
    filter_by_deadline_date?: boolean
    search?: string
    amount_min?: number
    amount_max?: number
  }): Promise<AnalyticsSummary> => {
    const response = await api.get('/api/analytics/summary', { params })
    return response.data
  },

  byBuyer: async (params?: {
    buyer?: string
    status?: string
    date_from?: string
    date_to?: string
    search?: string
  }): Promise<{ buyers: BuyerStats[]; total: number }> => {
    const response = await api.get('/api/analytics/by-buyer', { params })
    return response.data
  },

  byCategory: async (params?: {
    buyer?: string
    status?: string
    date_from?: string
    date_to?: string
    search?: string
  }): Promise<{ categories: CategoryStats[]; total: number }> => {
    const response = await api.get('/api/analytics/by-category', { params })
    return response.data
  },

  timeline: async (params?: {
    buyer?: string
    status?: string
    date_from?: string
    date_to?: string
    search?: string
  }): Promise<{ timeline: TimelinePoint[] }> => {
    const response = await api.get('/api/analytics/timeline', { params })
    return response.data
  },

  byWinner: async (params?: {
    buyer?: string
    status?: string
    date_from?: string
    date_to?: string
    search?: string
  }): Promise<{ winners: WinnerStats[]; total: number }> => {
    const response = await api.get('/api/analytics/by-winner', { params })
    return response.data
  },
}

// Coverage API interfaces
export interface CoverageStats {
  summary: {
    total: number
    scraped: number
    non_scraped: number
    coverage_percentage: number
  }
  by_date: Array<{
    date: string
    total: number
    scraped: number
    coverage: number
  }>
  by_category: Array<{
    category: string
    total: number
    scraped: number
    coverage: number
  }>
  by_buyer: Array<{
    buyer: string
    total: number
    scraped: number
    coverage: number
  }>
}

export const coverageApi = {
  getStats: async (params?: {
    date_from?: string
    date_to?: string
    filter_by_published_date?: boolean
    filter_by_deadline_date?: boolean
  }): Promise<CoverageStats> => {
    const response = await api.get('/coverage/stats', { params })
    return response.data
  },
}

export default api

