/**
 * System API Service
 * Handles system monitoring and update log operations
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface UpdateLog {
    run_id: string;
    timestamp: string;
    status: 'SUCCESS' | 'FAILED';
    metrics: {
        total_active_rechecked: number;
        status_changes_detected: number;
        new_tenders_added: number;
        total_tenders: number;
        errors: string[];
    };
    duration_seconds: number;
    data_file: string;
}

export interface UpdateLogsResponse {
    logs: UpdateLog[];
    latest_status: 'SUCCESS' | 'FAILED' | null;
    last_run_age_hours: number | null;
}

export interface SystemHealth {
    status: 'healthy' | 'warning';
    timestamp: string;
    checks: {
        [key: string]: {
            status: string;
            last_run?: string;
            last_status?: string;
            age_hours?: number;
            message?: string;
        };
    };
}

/**
 * Get update logs
 */
export const getUpdateLogs = async (): Promise<UpdateLogsResponse> => {
    const response = await axios.get(`${API_BASE_URL}/api/system/update-logs`);
    return response.data;
};

/**
 * Get system health
 */
export const getSystemHealth = async (): Promise<SystemHealth> => {
    const response = await axios.get(`${API_BASE_URL}/api/system/health`);
    return response.data;
};
