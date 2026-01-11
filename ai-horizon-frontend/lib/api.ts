import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { SubmitResponse, ChatResponse, SearchParams, StatsResponse, SkillsResponse, SkillItem, EvidenceDetail } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://ai-horizon-production.up.railway.app';
const SESSION_PREFIX = process.env.NEXT_PUBLIC_SESSION_PREFIX || 'horizon_';
const SESSION_KEY = `${SESSION_PREFIX}session`;

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Helper to get or create session ID
export const getSessionId = (): string => {
    if (typeof window === 'undefined') return '';

    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
        sessionId = uuidv4();
        localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
};

// Interceptors
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            if (error.response.status === 429) {
                // Rate limit
                console.error('Rate limit reached');
                // You might want to trigger a toast here if you have a global store or event emitter
            } else if (error.response.status === 503) {
                // Service unavailable
                console.error('Service unavailable');
            }
        }
        return Promise.reject(error);
    }
);

// API Functions
export const fetchStats = async (): Promise<StatsResponse> => {
    const { data } = await api.get<StatsResponse>('/api/stats');
    return data;
};

export const fetchSkills = async (): Promise<SkillItem[]> => {
    const { data } = await api.get<SkillsResponse>('/api/skills');
    return data.skills;  // Unwrap the skills array from response
};

export const fetchResources = async (params: SearchParams & { page?: number; limit?: number }) => {
    // Map job_role to role for the backend
    const backendParams: Record<string, string | number | undefined> = {
        page: params.page,
        limit: params.limit,
        role: params.job_role,  // Backend uses 'role' not 'job_role'
        resource_type: undefined,
        difficulty: undefined,
    };

    // Remove undefined values
    Object.keys(backendParams).forEach(key => {
        if (backendParams[key] === undefined) delete backendParams[key];
    });

    const { data } = await api.get('/api/resources', { params: backendParams });
    return data;
};

export const fetchResourceDetail = async (id: string): Promise<EvidenceDetail> => {
    const { data } = await api.get<EvidenceDetail>(`/api/evidence/artifact/${id}`);
    return data;
};

export const submitEvidence = async (payload: { url?: string; content?: string }): Promise<SubmitResponse> => {
    const { data } = await api.post('/api/submit', payload);
    return data;
};

export const sendChatMessage = async (message: string): Promise<ChatResponse> => {
    const session_id = getSessionId();
    const { data } = await api.post<ChatResponse>('/api/chat', { message, session_id });
    return data;
};
