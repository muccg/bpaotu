import { find, isNull, map, negate, toNumber } from 'lodash'
import reduceReducers from 'reduce-reducers'

import { combineActions, createActions, handleAction, handleActions } from 'redux-actions'

import { changeElementAtIndex, removeElementAtIndex } from '../../../reducers/utils'
import contextualDataDefinitionsReducer from './contextual_data_definitions'
import { searchPageInitialState } from './types'

export const { selectEnvironment, selectEnvironmentOperator, selectContextualFiltersMode } = createActions(
  'SELECT_ENVIRONMENT',
  'SELECT_ENVIRONMENT_OPERATOR',
  'SELECT_CONTEXTUAL_FILTERS_MODE'
)

const selectedEnvironmentReducer = handleActions(
  {
    [selectEnvironment as any]: (state, action: any) => ({
      ...state,
      value: action.payload
    }),
    [selectEnvironmentOperator as any]: (state, action: any) => ({
      ...state,
      operator: action.payload
    })
  },
  searchPageInitialState.filters.contextual.selectedEnvironment
)

const contextualFiltersModeReducer = handleAction(
  selectContextualFiltersMode,
  (state, action: any) => action.payload,
  searchPageInitialState.filters.contextual.filtersMode
)

/*
To keep things simple we don't use different object for different types. ex. String contextual filter would have a 
contains operator and only one value, Date contextual filter would have a between operator and from/to values etc.
There are pros and cons either way. This way the display of the React Components is fairly generic, but the state
will have multiple "values" fields that are empty if they don't make sense for the given type.
Ex. values is used only by Sample ID, String filters only use value, "Between" filters use value and value2 etc.
*/
const EmptyContextualFilter = {
  name: '',
  operator: '',
  value: '',
  value2: '',
  values: []
}

export const {
  selectContextualFilter,
  changeContextualFilterOperator,
  changeContextualFilterValue,
  changeContextualFilterValue2,
  changeContextualFilterValues,

  addContextualFilter,
  removeContextualFilter,
  clearContextualFilters
} = createActions(
  {
    SELECT_CONTEXTUAL_FILTER: (index, value) => ({ index, value }),
    CHANGE_CONTEXTUAL_FILTER_OPERATOR: (index, operator) => ({ index, operator }),
    CHANGE_CONTEXTUAL_FILTER_VALUE: (index, value) => ({ index, value }),
    CHANGE_CONTEXTUAL_FILTER_VALUE2: (index, value) => ({ index, value }),
    CHANGE_CONTEXTUAL_FILTER_VALUES: (index, values) => ({ index, values })
  },
  'ADD_CONTEXTUAL_FILTER',
  'REMOVE_CONTEXTUAL_FILTER',
  'CLEAR_CONTEXTUAL_FILTERS'
)

export const doesFilterMatchEnvironment = environment => filter => {
  if (environment.value === '') {
    return true
  }
  const eq = fltr => fltr.environment === toNumber(environment.value)
  const op = environment.operator === 'is' ? eq : negate(eq)
  return isNull(filter.environment) || op(filter)
}

const contextualFiltersReducer = handleActions(
  {
    [addContextualFilter as any]: (state: any, action) => ({
      ...state,
      filters: [...state.filters, EmptyContextualFilter]
    }),
    [removeContextualFilter as any]: (state: any, action) => ({
      ...state,
      filters: removeElementAtIndex(state.filters, action.payload)
    }),
    [clearContextualFilters as any]: (state: any, action) => ({
      ...state,
      filters: []
    }),
    [combineActions(selectEnvironment, selectEnvironmentOperator) as any]: (state, action) => ({
      ...state,
      filters: map(state.filters, f => {
        if (f.name === '') {
          return f
        }
        const dataDefinition = find(state.dataDefinitions.filters, dd => dd.name === f.name)
        return doesFilterMatchEnvironment(state.selectedEnvironment)(dataDefinition) ? f : EmptyContextualFilter
      })
    }),
    [selectContextualFilter as any]: (state: any, action: any) => ({
      ...state,
      filters: changeElementAtIndex(state.filters, action.payload.index, filter => ({
        ...EmptyContextualFilter,
        name: action.payload.value
      }))
    }),
    [changeContextualFilterOperator as any]: (state: any, action: any) => ({
      ...state,
      filters: changeElementAtIndex(state.filters, action.payload.index, filter => ({
        ...filter,
        operator: action.payload.operator
      }))
    }),
    [changeContextualFilterValue as any]: (state: any, action: any) => ({
      ...state,
      filters: changeElementAtIndex(state.filters, action.payload.index, filter => ({
        ...filter,
        value: action.payload.value
      }))
    }),
    [changeContextualFilterValue2 as any]: (state: any, action: any) => ({
      ...state,
      filters: changeElementAtIndex(state.filters, action.payload.index, filter => ({
        ...filter,
        value2: action.payload.value
      }))
    }),
    [changeContextualFilterValues as any]: (state: any, action: any) => ({
      ...state,
      filters: changeElementAtIndex(state.filters, action.payload.index, filter => ({
        ...filter,
        values: action.payload.values
      }))
    })
  },
  searchPageInitialState.filters.contextual.filters
)

const combinedContextualReducers = (state = searchPageInitialState.filters.contextual, action) => ({
  ...state,
  selectedEnvironment: selectedEnvironmentReducer(state.selectedEnvironment, action),
  dataDefinitions: contextualDataDefinitionsReducer(state.dataDefinitions, action),
  filtersMode: contextualFiltersModeReducer(state.filtersMode, action)
  // filters: array of filters is filled in here by the reduceReducers below
})

// This reducer is using reduceReducers because it needs access to both the dataDefinitions and the filters.
// Otherwise we could just use combineReducers just like for the other reducers in the app.
const contextualReducer = reduceReducers(combinedContextualReducers, contextualFiltersReducer)

export default contextualReducer
