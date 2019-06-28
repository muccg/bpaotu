import { findIndex, first, isEmpty, last, map, takeWhile } from 'lodash'
import { createAction } from 'redux-actions'

import { EmptyOperatorAndValue, EmptySelectableLoadableValues, searchPageInitialState, taxonomies } from './types'

import { getTaxonomy } from '../../../api'

// Generic Taxonomy Actions

const taxonomiesBefore = target => takeWhile(taxonomies, t => t !== target)
const taxonomiesAfter = target => taxonomies.slice(findIndex(taxonomies, t => t === target) + 1)

const fetchStarted = type => `FETCH_${type.toUpperCase()}_STARTED`
const fetchEnded = type => `FETCH_${type.toUpperCase()}_ENDED`

const fetchTaxonomyOptionsStarted = type => () => ({ type: fetchStarted(type) })

const fetchTaxonomyOptionsEnded = type => data => ({
  type: fetchEnded(type),
  payload: data
})

const clearTaxonomyFilter = type => () => ({ type: `CLEAR_${type.toUpperCase()}` })
const disableTaxonomyFilter = type => () => ({ type: `DISABLE_${type.toUpperCase()}` })

const taxonomyConfigFor = target => ({ type: target, taxonomies: taxonomiesBefore(target) })

const makeTaxonomyFetcher = config => () => (dispatch, getState) => {
  const state = getState()

  const selectedAmplicon = state.searchPage.filters.selectedAmplicon
  const selectedTaxonomies = map(config.taxonomies, taxonomy => state.searchPage.filters.taxonomy[taxonomy].selected)

  if (selectedTaxonomies.length > 0 && last(selectedTaxonomies).value === '') {
    dispatch(clearTaxonomyFilter(config.type)())
    return Promise.resolve()
  }

  dispatch(fetchTaxonomyOptionsStarted(config.type)())
  return getTaxonomy(selectedAmplicon, selectedTaxonomies)
    .then(data => {
      dispatch(fetchTaxonomyOptionsEnded(config.type)(data))
    })
    .catch(err => {
      dispatch(fetchTaxonomyOptionsEnded(config.type)(err))
    })
}

export const updateTaxonomyDropDowns = taxonomy => () => (dispatch, getState) => {
  const rest = taxonomy === '' ? taxonomies : taxonomiesAfter(taxonomy)

  if (isEmpty(rest)) {
    return Promise.resolve()
  }

  rest.forEach(t => dispatch(disableTaxonomyFilter(t)()))

  const nextTaxonomy = first(rest)

  const fetcher = makeTaxonomyFetcher(taxonomyConfigFor(nextTaxonomy))
  dispatch(fetcher()).then(() => {
    return dispatch(updateTaxonomyDropDowns(nextTaxonomy)())
  })
}

export const clearAllTaxonomyFilters = createAction('CLEAR_ALL_TAXONOMY_FILTERS')
export const fetchKingdoms = makeTaxonomyFetcher(taxonomyConfigFor('kingdom'))

// Generic taxonomy reducers

function makeTaxonomyReducer(taxonomyName) {
  return (state = EmptySelectableLoadableValues, action) => {
    const taxonomyU = taxonomyName.toUpperCase()
    const actionTypes = {
      clear: 'CLEAR_' + taxonomyU,
      disable: 'DISABLE_' + taxonomyU,
      fetchStarted: `FETCH_${taxonomyU}_STARTED`,
      fetchEnded: `FETCH_${taxonomyU}_ENDED`,
      select: 'SELECT_' + taxonomyU,
      selectOperator: `SELECT_${taxonomyU}_OPERATOR`
    }
    switch (action.type) {
      case clearAllTaxonomyFilters.toString():
      case actionTypes.clear:
        return EmptySelectableLoadableValues

      case actionTypes.disable:
        return {
          ...state,
          isDisabled: true
        }

      case actionTypes.fetchStarted:
        return {
          ...state,
          options: [],
          isLoading: true
        }

      case actionTypes.fetchEnded:
        const possibilites = action.payload.data.possibilities.new_options.possibilities
        const options = map(possibilites, (option: any) => ({ id: option[0], value: option[1] }))

        const isSelectedStillInOptions = selectedOption => {
          if (selectedOption.value === '') {
            return true
          }
          return findIndex(options, (k: HTMLOptionElement) => k.id === selectedOption.value) !== -1
        }

        const selected = isSelectedStillInOptions(state.selected) ? state.selected : EmptyOperatorAndValue

        return {
          isLoading: false,
          options,
          selected
        }

      case actionTypes.select:
        return {
          ...state,
          selected: {
            ...state.selected,
            value: action.payload
          }
        }
      case actionTypes.selectOperator:
        return {
          ...state,
          selected: {
            ...state.selected,
            operator: action.payload
          }
        }
    }
    return state
  }
}

export default function taxonomyReducer(state = searchPageInitialState.filters.taxonomy, action) {
  return {
    ...state,
    kingdom: makeTaxonomyReducer('kingdom')(state.kingdom, action),
    phylum: makeTaxonomyReducer('phylum')(state.phylum, action),
    class: makeTaxonomyReducer('class')(state.class, action),
    order: makeTaxonomyReducer('order')(state.order, action),
    family: makeTaxonomyReducer('family')(state.family, action),
    genus: makeTaxonomyReducer('genus')(state.genus, action),
    species: makeTaxonomyReducer('species')(state.species, action)
  }
}
