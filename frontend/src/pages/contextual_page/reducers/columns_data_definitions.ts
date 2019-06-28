import { createActions, handleActions } from 'redux-actions'

import { getContextualDataDefinitions } from '../../../api'
import { handleSimpleAPIResponse } from '../../../reducers/utils'

const { fetchColumnsDataDefinitionsStarted, fetchColumnsDataDefinitionsEnded } = createActions(
  'FETCH_COLUMNS_DATA_DEFINITIONS_STARTED',
  'FETCH_COLUMNS_DATA_DEFINITIONS_ENDED'
)

export function fetchColumnsDataDefinitions() {
  return (dispatch: any) => {
    dispatch(fetchColumnsDataDefinitionsStarted())
    handleSimpleAPIResponse(dispatch, getContextualDataDefinitions, fetchColumnsDataDefinitionsEnded)
  }
}

const initialState = {
  isLoading: false,
  values: []
}

export default handleActions(
  {
    [fetchColumnsDataDefinitionsStarted as any]: (state, action) => ({
      isLoading: true,
      values: []
    }),
    [fetchColumnsDataDefinitionsEnded as any]: (state, action: any) => ({
      isLoading: false,
      values: action.payload.data.definitions
    })
  },
  initialState
)
