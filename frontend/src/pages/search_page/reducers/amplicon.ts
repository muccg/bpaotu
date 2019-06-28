import { createActions, handleActions } from 'redux-actions'

import { clearAllTaxonomyFilters } from './taxonomy'
import { EmptyOperatorAndValue } from './types'

export const { selectAmplicon, selectAmpliconOperator } = createActions('SELECT_AMPLICON', 'SELECT_AMPLICON_OPERATOR')

export default handleActions(
  {
    [clearAllTaxonomyFilters as any]: (state, action: any) => {
      return EmptyOperatorAndValue
    },
    [selectAmplicon as any]: (state, action: any) => ({
      ...state,
      value: action.payload
    }),
    [selectAmpliconOperator as any]: (state, action: any) => ({
      ...state,
      operator: action.payload
    })
  },
  EmptyOperatorAndValue
)
