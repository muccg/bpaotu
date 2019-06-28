import { map, partial } from 'lodash'
import { createActions, handleActions } from 'redux-actions'
import { executeSampleSitesSearch } from '../../../api'
import { handleSimpleAPIResponse } from '../../../reducers/utils'
import { describeSearch } from './search'
import { searchPageInitialState } from './types'

export const {
  openSamplesMapModal,
  closeSamplesMapModal,

  samplesMapModalFetchSamplesStarted,
  samplesMapModalFetchSamplesEnded
} = createActions(
  'OPEN_SAMPLES_MAP_MODAL',
  'CLOSE_SAMPLES_MAP_MODAL',

  'SAMPLES_MAP_MODAL_FETCH_SAMPLES_STARTED',
  'SAMPLES_MAP_MODAL_FETCH_SAMPLES_ENDED',
)

export const fetchSampleMapModalSamples = () => (dispatch, getState) => {
  const filters = describeSearch(getState().searchPage.filters)

  dispatch(samplesMapModalFetchSamplesStarted())
  handleSimpleAPIResponse(dispatch, partial(executeSampleSitesSearch, filters), samplesMapModalFetchSamplesEnded)
}

export default handleActions(
  {
    [openSamplesMapModal as any]: (state, action) => ({
      ...state,
      isOpen: true
    }),
    [closeSamplesMapModal as any]: (state, action) => ({
      ...state,
      isOpen: false
    }),
    [samplesMapModalFetchSamplesStarted as any]: (state, action) => ({
      ...state,
      isLoading: true,
      markers: []
    }),
    [samplesMapModalFetchSamplesEnded as any]: (state, action: any) => ({
      ...state,
      isLoading: false,
      markers: map(action.payload.data.data, sample => ({
        bpadata: sample.bpa_data,
        lat: sample.latitude,
        lng: sample.longitude,
        site_images: sample.site_images
      }))
    })
  },
  searchPageInitialState.samplesMapModal
)
