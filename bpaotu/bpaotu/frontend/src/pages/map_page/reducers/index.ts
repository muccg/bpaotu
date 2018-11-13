import { map, partial } from 'lodash'
import { createActions, handleActions } from 'redux-actions'
import { executeSampleSitesSearch, executeImageSearch } from '../../../api'
import { handleSimpleAPIResponse, changeElementAtIndex } from '../../../reducers/utils'
import { EmptyOTUQuery } from '../../../search'

export const {
    samplesMapFetchSamplesStarted,
    samplesMapFetchSamplesEnded,

    samplesMapFetchImagesStarted,
    samplesMapFetchImagesEnded
} = createActions(
  'SAMPLES_MAP_FETCH_SAMPLES_STARTED',
  'SAMPLES_MAP_FETCH_SAMPLES_ENDED',

  'SAMPLES_MAP_FETCH_IMAGES_STARTED',
  'SAMPLES_MAP_FETCH_IMAGES_ENDED'
)

export const fetchSampleMapSamples = () => dispatch => {
  const fetchAllSamples = partial(executeSampleSitesSearch, EmptyOTUQuery)

  dispatch(samplesMapFetchSamplesStarted())
  handleSimpleAPIResponse(dispatch, fetchAllSamples, samplesMapFetchSamplesEnded)
}


const x = () => dispatch => {

}

// export const fetchSampleMapImages = (index, lat, lng) => () => dispatch => {
export const fetchSampleMapImages = (index, lat, lng) => {
    () => dispatch => {
      console.log(dispatch);

    function mapIdToImage(...args) {
        const action : any = samplesMapFetchImagesEnded(...args);
        action.payload.index = index;

        return action;
    }

    dispatch(samplesMapFetchImagesStarted())
    handleSimpleAPIResponse(dispatch, () => executeImageSearch(lat, lng), mapIdToImage)
}


const initialState = {
  isLoading: false,
  samples: []
}

export default handleActions(
  {
    [samplesMapFetchSamplesStarted as any]: (state, action) => ({
      ...state,
      isLoading: true,
      samples: []
    }),
    [samplesMapFetchSamplesEnded as any]: (state, action: any) => ({
      ...state,
      isLoading: false,
      samples: map(action.payload.data.data, sample => ({
        bpadata: sample.bpa_data,
        lat: sample.latitude,
        lng: sample.longitude,
        img_urls: []
      }))
    }),
    [samplesMapFetchImagesStarted as any]: (state, action) => ({
        ...state,
        // isLoadingImages: true,
    }),
    [samplesMapFetchImagesEnded as any]: (state, action: any) => ({
        ...state,
        samples: changeElementAtIndex(state.samples, action.payload.index, (sample) => ({
            ...sample,
            isLoadingImages: false,
            img_urls: action.payload.data
        }))
    })
  },
  initialState
)
