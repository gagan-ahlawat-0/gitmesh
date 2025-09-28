
export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    requested_files?: Array<{
      path: string;
      reason: string;
      branch?: string;
      auto_add?: boolean;
      metadata?: Record<string, any>;
    }>;
    interactive_elements?: Array<{
      element_type: string;
      value: string;
      label: string;
      metadata?: Record<string, any>;
    }>;
    file_requests_count?: number;
    [key: string]: any;
  };
}

export interface Chat {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}
