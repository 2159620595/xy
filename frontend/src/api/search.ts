import { post } from '@/utils/request'
import type { SearchResultItem } from '@/types'

export const searchItems = async (
  keyword: string,
  page: number = 1,
  pageSize: number = 20,
): Promise<{
  success: boolean
  data: SearchResultItem[]
  total?: number
  error?: string
}> => {
  const result = await post<{
    success: boolean
    data?: SearchResultItem[]
    total?: number
    error?: string
  }>('/items/search', { keyword, page, page_size: pageSize })

  return {
    success: result.success,
    data: result.data || [],
    total: result.total,
    error: result.error,
  }
}
