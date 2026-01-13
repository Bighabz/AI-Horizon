export interface Skill {
    task_id: string;
    task_name: string;
    description: string;
    classification: "Replace" | "Augment" | "Remain Human" | "New Task";
    confidence: number;
    evidence_count: number;
    work_roles: string[];
    category?: string;
}

export type SearchResult = Skill;

export interface Resource {
    artifact_id: string;
    title: string;
    source_url: string | null;
    classification: string;
    confidence: number;
    rationale: string;
    stored_at: string;
    // UI requirements addition
    resource_type: string;
    difficulty: string;
    is_free: boolean;
    work_roles: string[];
    work_role?: string | null;
    submission_type?: "evidence" | "resource";
}

export interface SubmitResponse {
    success: boolean;
    artifact_id?: string;
    is_duplicate: boolean;
    is_relevant?: boolean;
    relevance_score?: number;
    relevance_reason?: string;
    stored?: boolean;
    message: string;
    classification?: {
        classification: string;
        confidence: number;
        rationale: string;
        is_relevant?: boolean;
        relevance_score?: number;
        relevance_reason?: string;
        submission_type?: "evidence" | "resource";
        dcwf_tasks: Array<{
            task_id: string;
            task_name: string;
            impact_description: string;
        }>;
        work_roles: string[];
        key_findings: string[];
    };
}

export interface ChatResponse {
    output: string;  // Backend returns "output" not "response"
    sources: string[];  // Backend returns array of URL strings
    session_id: string;
}

// Stats response from /api/stats
export interface StatsResponse {
    total_tasks: number;
    total_resources: number;
    free_resources: number;
    classified_artifacts: number;
    classifications: {
        replace: number;
        augment: number;
        remain_human: number;
        new_task: number;
    };
    resource_types: Record<string, number>;
    difficulty_levels: Record<string, number>;
    avg_confidence: number;
    last_updated: string;
}

// Skills response from /api/skills
export interface SkillsResponse {
    skills: SkillItem[];
    total: number;
}

export interface SkillItem {
    name: string;
    id: string;
    category: string;
    priority: string;
    total_resources: number;
    free_resources: number;
    evidence_count: number;
    resource_count: number;
    classifications: {
        Replace: number;
        Augment: number;
        "Remain Human": number;
        "New Task": number;
    };
    slug: string;
}

// Evidence/Artifact detail
export interface EvidenceDetail {
    artifact_id: string;
    title: string;
    content?: string;
    source_url: string | null;
    source_type: string;
    resource_type: string;
    difficulty: string;
    is_free: boolean;
    work_role: string | null;
    work_roles: string[];
    submission_type?: "evidence" | "resource";
    classification: string;
    confidence: number;
    rationale: string;
    dcwf_tasks: Array<{
        task_id: string;
        task_name: string;
        impact_description?: string;
        relevance_score?: number;
    }>;
    key_findings: string[];
    ai_tools_mentioned: string[];
    stored_at: string;
}

export interface SearchParams {
    query?: string;
    job_role?: string;
    dcwf_task?: string;
    ai_tool?: string;
    classification?: string;
    limit?: number;
}
