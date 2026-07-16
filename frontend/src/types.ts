export type SortKey = 'top' | 'new'

export interface FeatureRequest {
  id: number
  title: string
  description: string
  created_at: string
  vote_count: number
  has_voted: boolean
  is_author: boolean
}

export interface VoteResult {
  request_id: number
  vote_count: number
  has_voted: boolean
}
