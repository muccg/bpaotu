import * as _ from 'lodash';
import { executeSampleSitesSearch } from "../../../api";
import { createActions, handleActions } from 'redux-actions';
import { handleSimpleAPIResponse } from '../../../reducers/utils';
import { EmptyOTUQuery } from '../../../search';


export const {
    samplesMapFetchSamplesStarted,
    samplesMapFetchSamplesEnded,
} = createActions(
    'SAMPLES_MAP_FETCH_SAMPLES_STARTED',
    'SAMPLES_MAP_FETCH_SAMPLES_ENDED',
);

export const fetchSampleMapSamples = () => (dispatch) => {
    const fetchAllSamples = _.partial(executeSampleSitesSearch, EmptyOTUQuery);

    dispatch(samplesMapFetchSamplesStarted());
    handleSimpleAPIResponse(dispatch, fetchAllSamples, samplesMapFetchSamplesEnded);
}

const initialState = {
    isLoading: false,
    samples: [],
}

export default handleActions({
    [samplesMapFetchSamplesStarted as any]: (state, action) => ({
        ...state,
        isLoading: true,
        samples: [],
    }),
    [samplesMapFetchSamplesEnded as any]: (state, action: any) => ({
        ...state,
        isLoading: false,
        samples: _.map(action.payload.data.data, sample => ({bpadata: sample.bpa_data, lat: sample.latitude, lng: sample.longitude})),
    }),
}, initialState);
