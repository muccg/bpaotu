import { combineReducers } from 'redux'

import searchResultsReducer from './search'
import selectColumnsReducer from './select_columns'

const pageReducer = combineReducers({
  selectColumns: selectColumnsReducer,
  results: searchResultsReducer
})

export default pageReducer
