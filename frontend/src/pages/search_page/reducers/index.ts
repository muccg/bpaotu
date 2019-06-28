import { combineReducers } from 'redux'

import selectedAmpliconReducer from './amplicon'
import blastSearchReducer from './blast_search'
import contextualReducer from './contextual'
import samplesMapModalReducer from './samples_map_modal'
import searchResultsReducer from './search'
import submitToGalaxyReducer from './submit_to_galaxy'
import taxonomyReducer from './taxonomy'
import tipsReducer from './tips'

const filtersReducer = combineReducers({
  selectedAmplicon: selectedAmpliconReducer,
  taxonomy: taxonomyReducer,
  contextual: contextualReducer
})

const pageReducer = combineReducers({
  filters: filtersReducer,
  samplesMapModal: samplesMapModalReducer,
  galaxy: submitToGalaxyReducer,
  tips: tipsReducer,
  results: searchResultsReducer,
  blastSearch: blastSearchReducer
})

export default pageReducer
