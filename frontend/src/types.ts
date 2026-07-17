export type SortMode = "top" | "new" | "trending";

export interface FeatureRequest {
  id: number;
  title: string;
  description: string;
  author: string;
  vote_count: number;
  has_voted: boolean;
  created_at: string;
}

export interface Page {
  items: FeatureRequest[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}
