import { combineReducers } from 'redux'
import ampliconsReducer from './amplicons'

export default combineReducers({
  amplicons: ampliconsReducer
})
