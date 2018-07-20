import * as _ from 'lodash';
import * as moment from 'moment';
import { createActions, handleActions } from 'redux-actions';
import axios from 'axios';

import { ckanAuthInfo } from '../api';

import { handleSimpleAPIResponse } from './utils';

const {
    ckanAuthInfoStarted,
    ckanAuthInfoEnded,
} = createActions(
    'CKAN_AUTH_INFO_STARTED',
    'CKAN_AUTH_INFO_ENDED',
)

export { ckanAuthInfoStarted , ckanAuthInfoEnded };

export const getCKANAuthInfo = () => (dispatch, getState) => {
    const state = getState();

    dispatch(ckanAuthInfoStarted());
    handleSimpleAPIResponse(dispatch, ckanAuthInfo, ckanAuthInfoEnded);
};

const initialState: any = {
    ckanAuthToken: null,
    isLoginInProgress: false,
    isLoggedIn: false,
    email: null,
};

export default handleActions({
    [ckanAuthInfoStarted as any]: (state: any, action: any) => {
        return {
            ...state,
            isLoginInProgress: true,
        };
    },
    [ckanAuthInfoEnded as any]: {
        next: (state: any, action: any) => {
            const ckanAuthToken = action.payload.data;
            const [_, data] = ckanAuthToken.split('||');
            const { email } = JSON.parse(data);
            axios.defaults.headers = {
                'X-BPAOTU-CKAN-Token': ckanAuthToken,
            }
            return {
                isLoginInProgess: false,
                isLoggedIn: true,
                ckanAuthToken,
                email,
            };
        },
        throw: (state, action) => {
            return initialState;
        }
    }
}, initialState);