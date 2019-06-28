import { find, get as _get, isEmpty, map, reject, uniq } from 'lodash'
import { createActions, handleActions } from 'redux-actions'

import { executeSearch } from '../../../api'
import { submitToGalaxyEnded, submitToGalaxyStarted } from './submit_to_galaxy'
import { ErrorList, searchPageInitialState, taxonomies } from './types'

export const { changeTableProperties, searchStarted, searchEnded } = createActions(
  'CHANGE_TABLE_PROPERTIES',
  'SEARCH_STARTED',
  'SEARCH_ENDED'
)

function marshallContextualFilters(filtersState, dataDefinitions) {
  const filterDataDefinition = name => find(dataDefinitions.filters, dd => dd.name === name)
  const filters = map(reject(filtersState, filter => filter.name === ''), filter => {
    const dataDefinition = filterDataDefinition(filter.name)

    const values: any = {}
    switch (dataDefinition.type) {
      case 'string':
        values.contains = filter.value
        break
      case 'float':
      case 'date':
        values.from = filter.value
        values.to = filter.value2
        break
      case 'ontology':
        values.is = filter.value
        break
      case 'sample_id':
        values.is = filter.values
        break
    }
    return {
      field: filter.name,
      operator: filter.operator,
      ...values
    }
  })

  return filters
}

function marshallContextual(state) {
  const { selectedEnvironment, filtersMode } = state

  return {
    environment: selectedEnvironment.value === '' ? null : selectedEnvironment,
    mode: filtersMode,
    filters: marshallContextualFilters(state.filters, state.dataDefinitions)
  }
}

export const describeSearch = stateFilters => {
  const selectedAmplicon = stateFilters.selectedAmplicon
  const selectedTaxonomies = map(taxonomies, taxonomy => stateFilters.taxonomy[taxonomy].selected)

  return {
    amplicon_filter: selectedAmplicon,
    taxonomy_filters: selectedTaxonomies,
    contextual_filters: marshallContextual(stateFilters.contextual)
  }
}

export const search = () => (dispatch, getState) => {
  const state = getState()

  dispatch(searchStarted())

  const filters = describeSearch(state.searchPage.filters)

  const options = {
    ...state.searchPage.results,
    columns: uniq(reject(map(filters.contextual_filters.filters, f => f.field), name => isEmpty(name)))
  }

  executeSearch(filters, options)
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
    },
    [submitToGalaxyStarted as any]: (state, action) => ({
      ...state,
      errors: []
    }),
    [submitToGalaxyEnded as any]: {
      next: (state, action: any) => state,
      throw: (state, action: any) => ({
        ...state,
        errors: action.payload.msgs
      })
    }
  },
  searchPageInitialState.results
)
