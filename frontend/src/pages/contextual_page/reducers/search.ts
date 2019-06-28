import { get as _get, isEmpty, map, reject } from 'lodash'
import { createActions, handleActions } from 'redux-actions'

import { executeContextualSearch } from '../../../api'
import { ErrorList, taxonomies } from '../../../pages/search_page/reducers/types'
import { EmptyOTUQuery } from '../../../search'

export const { changeTableProperties, searchStarted, searchEnded } = createActions({
  CONTEXTUAL_PAGE: {
    CHANGE_TABLE_PROPERTIES: undefined,
    SEARCH_STARTED: undefined,
    SEARCH_ENDED: undefined
  }
}).contextualPage as any

export const search = () => (dispatch, getState) => {
  const state = getState()

  dispatch(searchStarted())

  const filters = EmptyOTUQuery
  const options = {
    ...state.contextualPage.results,
    columns: reject(map(state.contextualPage.selectColumns.columns, c => c.name), name => isEmpty(name))
  }

  executeContextualSearch(filters, options)
    .then(data => {
      if (_get(data, 'data.errors', []).length > 0) {
        dispatch(searchEnded(new ErrorList(...data.data.errors)))
        return
      }
      dispatch(searchEnded(data))
    })
    .catch(error => {
      dispatch(searchEnded(new ErrorList('Unhandled server-side error!')))
    })
}

const resultsInitialState = {
  isLoading: false,
  errors: [],
  data: [],
  page: 0,
  pageSize: 10,
  rowsCount: 0,
  sorted: []
}

export default handleActions(
  {
    [changeTableProperties as any]: (state, action: any) => {
      const { page, pageSize, sorted } = action.payload
      return {
        ...state,
        page,
        pageSize,
        sorted
      }
    },
    [searchStarted as any]: (state, action: any) => ({
      ...state,
      errors: [],
      isLoading: true
    }),
    [searchEnded as any]: {
      next: (state, action: any) => {
        const rowsCount = action.payload.data.rowsCount
        const pages = Math.ceil(rowsCount / state.pageSize)
        const newPage = Math.min(pages - 1 < 0 ? 0 : pages - 1, state.page)
        return {
          ...state,
          isLoading: false,
          data: action.payload.data.data,
          rowsCount,
          pages,
          page: newPage
        }
      },
      throw: (state, action: any) => ({
        ...state,
        isLoading: false,
        errors: action.payload.msgs
      })
    }
  },
  resultsInitialState
)
