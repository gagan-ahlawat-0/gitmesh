
export interface NeuralNodeData {
  id: string;
  title: string;
  type: 'note' | 'link' | 'file' | 'image' | 'project';
  content?: string;
  connections: string[];
  size?: number;
  x?: number;
  y?: number;
  color?: string;
}

export interface Project {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'completed';
}

export interface UserProfile {
  name: string;
  email: string;
  avatar?: string;
  description?: string;
  links?: {
    title: string;
    url: string;
  }[];
  projects?: Project[];
}

// GitHub User Profile Types
export interface GitHubUser {
  id: number;
  login: string;
  name: string;
  bio: string;
  avatar_url: string;
  html_url: string;
  followers: number;
  following: number;
  public_repos: number;
  company: string;
  location: string;
  email: string;
  blog: string;
  twitter_username: string;
  created_at: string;
  updated_at: string;
  organizations?: GitHubOrganization[];
}

export interface GitHubOrganization {
  id: number;
  login: string;
  name: string;
  description: string;
  avatar_url: string;
  html_url: string;
}

export interface GitHubUserActivity {
  id: string;
  type: string;
  actor: {
    login: string;
    avatar_url: string;
  };
  repo: {
    name: string;
  };
  created_at: string;
  payload: any;
}

export interface GitHubAchievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  earnedAt: string;
}

export interface ImportSource {
  id: string;
  name: string;
  type: 'csv' | 'api' | 'url' | 'file' | 'text' | 'branch' | 'control-panel';
  icon: string;
  description: string;
}
