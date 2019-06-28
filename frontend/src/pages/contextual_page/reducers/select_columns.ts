import { combineReducers } from 'redux'

import { createActions, handleActions } from 'redux-actions'

import { changeElementAtIndex, removeElementAtIndex } from '../../../reducers/utils'
import columnsDataDefinitionsReducer from './columns_data_definitions'

export const {
  selectColumn,

  addColumn,
  removeColumn,
  clearColumns
} = createActions(
  {
    SELECT_COLUMN: (index, value) => ({ index, value })
  },
  'ADD_COLUMN',
  'REMOVE_COLUMN',
  'CLEAR_COLUMNS'
)

const EmptyColumn = {
  name: '',
  value: ''
}

const columnsReducer = handleActions(
  {
    [addColumn as any]: (state: any, action) => [...state, EmptyColumn],
    [removeColumn as any]: (state: any, action) => removeElementAtIndex(state, action.payload),
    [clearColumns as any]: (state: any, action) => [],
    [selectColumn as any]: (state: any, action: any) =>
      changeElementAtIndex(state, action.payload.index, filter => ({
        ...EmptyColumn,
        name: action.payload.value
      }))
  },
  []
)

export default combineReducers({
  columns: columnsReducer,
  dataDefinitions: columnsDataDefinitionsReducer
})
