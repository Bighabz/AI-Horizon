import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Types for the document_registry table
export interface DocumentRecord {
  id: string;
  user_id?: string;
  username?: string;
  chat_id?: string;
  file_name: string;
  source_type: string;
  source_url?: string;
  classification: 'Replace' | 'Augment' | 'Remain Human' | 'New Task';
  confidence: number;
  rationale?: string;
  dcwf_tasks: string[];
  key_findings: string[];
  scores?: Record<string, number>;
  pdf_url?: string;
  content_length?: number;
  extraction_method?: string;
  created_at: string;
}
