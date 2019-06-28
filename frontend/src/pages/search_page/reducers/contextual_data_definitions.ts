import { find, map, reject } from 'lodash'
import { createActions, handleActions } from 'redux-actions'

import { getContextualDataDefinitions } from '../../../api'
import { handleSimpleAPIResponse } from '../../../reducers/utils'

const { fetchContextualDataDefinitionsStarted, fetchContextualDataDefinitionsEnded } = createActions(
  'FETCH_CONTEXTUAL_DATA_DEFINITIONS_STARTED',
  'FETCH_CONTEXTUAL_DATA_DEFINITIONS_ENDED'
)

export function fetchContextualDataDefinitions() {
  return (dispatch: any) => {
    dispatch(fetchContextualDataDefinitionsStarted())
    handleSimpleAPIResponse(dispatch, getContextualDataDefinitions, fetchContextualDataDefinitionsEnded)
  }
}

const initialState = {
  isLoading: false,
  environment: [],
  filters: []
}

export default handleActions(
  {
    [fetchContextualDataDefinitionsStarted as any]: (state, action) => ({
      ...initialState,
      isLoading: true
    }),
    [fetchContextualDataDefinitionsEnded as any]: (state, action: any) => {
      const isEnvironment = definition => definition.name === 'environment_id'
      const environment = find(action.payload.data.definitions, isEnvironment)
      const allButEnvironment = reject(action.payload.data.definitions, isEnvironment)
      return {
        isLoading: false,
        environment: map(environment.values, ([id, name]) => ({ id, name })),
        filters: allButEnvironment
      }
    }
  },
  initialState
)
