import { map } from 'lodash'
import { createActions, handleAction } from 'redux-actions'

import { getAmplicons } from '../../api'

import { handleSimpleAPIResponse } from '../utils'

export const { fetchAmpliconsStarted, fetchAmpliconsEnded } = createActions(
  'FETCH_AMPLICONS_STARTED',
  'FETCH_AMPLICONS_ENDED'
)

export function fetchAmplicons() {
  return (dispatch: any) => {
    dispatch(fetchAmpliconsStarted())
    handleSimpleAPIResponse(dispatch, getAmplicons, fetchAmpliconsEnded)
  }
}

const initialState = {
  isLoading: true,
  values: [],
  error: false
}

export default handleAction(
  fetchAmpliconsEnded,
  {
    next: (state, action: any) => ({
      isLoading: false,
      error: false,
      values: map(action.payload.data.possibilities, (option: any) => ({ id: option[0], value: option[1] }))
    }),
    throw: (state, action: any) => {
      // tslint:disable-next-line:no-console
      console.error('Error while loading amplicons: ', action.payload)
      return {
        isLoading: false,
        error: true,
        values: []
      }
    }
  },
  initialState
)
