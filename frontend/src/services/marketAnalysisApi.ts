/**
 * Market Analysis API Service
 * Handles all API calls for market analysis dashboard
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface KPIs {
    total_tenders: number;
    avg_inflation: number;
    total_market_volume: number;
}

export interface PriceTrend {
    regions: string[];
    years: number[];
    data: {
        [region: string]: {
            [year: string]: number | null;
            inflation_5y: number;
        };
    };
}

export interface Winner {
    name: string;
    total_wins: number;
    total_value: number;
    regions: string[];
}

export interface MarketShare {
    top_winners: Winner[];
}

export interface FailureRegion {
    name: string;
    total: number;
    failed: number;
    failure_rate: number;
}

export interface Failures {
    regions: FailureRegion[];
}

export interface HotOpportunities {
    opportunities: FailureRegion[];
}

/**
 * Get overall market KPIs
 */
export const getKPIs = async (): Promise<KPIs> => {
    const response = await axios.get(`${API_BASE_URL}/api/analysis/kpis`);
    return response.data;
};

/**
 * Get price trends by region and year
 */
export const getPriceTrends = async (): Promise<PriceTrend> => {
    const response = await axios.get(`${API_BASE_URL}/api/analysis/price-trends`);
    return response.data;
};

/**
 * Get market share by top winners
 */
export const getMarketShare = async (): Promise<MarketShare> => {
    const response = await axios.get(`${API_BASE_URL}/api/analysis/market-share`);
    return response.data;
};

/**
 * Get failure rates by region
 */
export const getFailures = async (): Promise<Failures> => {
    const response = await axios.get(`${API_BASE_URL}/api/analysis/failures`);
    return response.data;
};

/**
 * Get hot opportunities (regions with recent failures)
 */
export const getHotOpportunities = async (): Promise<HotOpportunities> => {
    const response = await axios.get(`${API_BASE_URL}/api/analysis/hot-opportunities`);
    return response.data;
};
