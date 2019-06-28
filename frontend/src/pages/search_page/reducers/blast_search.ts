import { filter, get as _get, includes, isNumber, join, last, reject, upperCase } from 'lodash'
import { createActions, handleActions } from 'redux-actions'

import { executeBlast, getBlastSubmission } from '../../../api'
import { changeElementAtIndex, removeElementAtIndex } from '../../../reducers/utils'

import { describeSearch } from './search'
import { BlastSubmission, ErrorList } from './types'

export const HANDLE_BLAST_SEQUENCE = 'HANDLE_BLAST_SEQUENCE'
export const RUN_BLAST_STARTED = 'RUN_BLAST_STARTED'
export const RUN_BLAST_ENDED = 'RUN_BLAST_ENDED'
export const BLAST_SUBMISSION_UPDATE_STARTED = 'BLAST_SUBMISSION_UPDATE_STARTED'
export const BLAST_SUBMISSION_UPDATE_ENDED = 'BLAST_SUBMISSION_UPDATE_ENDED'
export const CLEAR_BLAST_ALERT = 'CLEAR_BLAST_ALERT'

const BLAST_SUBMISSION_POLL_FREQUENCY_MS = 5000

export const {
  handleBlastSequence,

  runBlastStarted,
  runBlastEnded,

  blastSubmissionUpdateStarted,
  blastSubmissionUpdateEnded,

  clearBlastAlert
} = createActions(
  HANDLE_BLAST_SEQUENCE,

  RUN_BLAST_STARTED,
  RUN_BLAST_ENDED,

  BLAST_SUBMISSION_UPDATE_STARTED,
  BLAST_SUBMISSION_UPDATE_ENDED,

  CLEAR_BLAST_ALERT
)

const blastInitialState = {
  sequenceValue: '',
  alerts: [],
  isSubmitting: false,
  submissions: []
}

export const runBlast = () => (dispatch, getState) => {
  const state = getState()

  dispatch(runBlastStarted())

  const filters = describeSearch(state.searchPage.filters)
  const searchString = state.searchPage.blastSearch.sequenceValue

  executeBlast(searchString, filters)
    .then(data => {
      if (_get(data, 'data.errors', []).length > 0) {
        dispatch(runBlastEnded(new ErrorList(data.data.errors)))
        return
      }
      dispatch(runBlastEnded(data))
      dispatch(autoUpdateBlastSubmission())
    })
    .catch(error => {
      dispatch(runBlastEnded(new ErrorList('Unhandled server-side error!')))
    })
}
export const autoUpdateBlastSubmission = () => (dispatch, getState) => {
  const getLastSubmission: (() => BlastSubmission) = () => last(getState().searchPage.blastSearch.submissions)
  const lastSubmission = getLastSubmission()
  getBlastSubmission(lastSubmission.submissionId)
    .then(data => {
      dispatch(blastSubmissionUpdateEnded(data))
      const newLastSubmission = getLastSubmission()
      if (!newLastSubmission.finished) {
        setTimeout(() => dispatch(autoUpdateBlastSubmission()), BLAST_SUBMISSION_POLL_FREQUENCY_MS)
      }
    })
    .catch(error => {
      dispatch(blastSubmissionUpdateEnded(new Error('Unhandled server-side error!')))
    })
}
function alert(text, color = 'primary') {
  return { color, text }
}

const BLAST_ALERT_IN_PROGRESS = alert('BLAST search is in progress, and may take several minutes. Do not close your browser - this status will update once the search is complete.')
const BLAST_ALERT_ERROR = alert('An error occured while running BLAST.', 'danger')

export default handleActions(
  {
    [handleBlastSequence as any]: (state, action: any) => ({
      ...state,
      sequenceValue: join(filter(upperCase(action.payload), ch => includes('GATC', ch)), '')
    }),
    [runBlastStarted as any]: (state, action: any) => ({
      ...state,
      isSubmitting: true
    }),
    [runBlastEnded as any]: {
      next: (state, action: any) => {
        const lastSubmission: BlastSubmission = {
          submissionId: action.payload.data.submission_id,
          finished: false,
          succeeded: false
        }
        const alerts = [BLAST_ALERT_IN_PROGRESS]

        return {
          ...state,
          sequenceValue: state.sequenceValue,
          alerts,
          submissions: [...state.submissions, lastSubmission]
        }
      },
      throw: (state, action: any) => ({
        ...state,
        isSubmitting: false,
        alerts: [BLAST_ALERT_ERROR]
      })
    },
    [blastSubmissionUpdateEnded as any]: {
      next: (state, action: any) => {
        const lastSubmission = last(state.submissions)
        const newLastSubmissionState = (submission => {
          const { state: status, error } = action.payload.data.submission
          const newState = {
            ...submission,
            finished: status === 'complete' || status === 'error',
            succeeded: status === 'complete'
          }
          if (status === 'error') {
            newState['error'] = error
          }
          return newState
        })(lastSubmission)
        let newAlerts: any = state.alerts
        if (newLastSubmissionState['finished'] && !lastSubmission['finished']) {
          const resultUrl = action.payload.data.submission.result_url
          const BLAST_ALERT_SUCCESS = alert(
            'BLAST search executed successfully. ' +
              `Click <a target="_blank" href="${resultUrl}" className="alert-link">` +
              'here</a> to download the results.',
            'success'
          )
          newAlerts = reject([state.alerts, BLAST_ALERT_IN_PROGRESS])
          newAlerts.push(newLastSubmissionState['succeeded'] ? BLAST_ALERT_SUCCESS : BLAST_ALERT_ERROR)
        }

        let isSubmitted: any = state.isSubmitting
        if (action.payload.data.submission.result_url) {
          isSubmitted = false
        }

        return {
          ...state,
          submissions: changeElementAtIndex(
            state.submissions,
            state.submissions.length - 1,
            _ => newLastSubmissionState
          ),
          alerts: newAlerts,
          isSubmitting: isSubmitted
        }
      },
      throw: (state, action) => {
        const lastSubmission = last(state.submissions)
        return {
          ...state,
          submissions: changeElementAtIndex(state.submissions, state.submissions.length - 1, submission => ({
            ...submission,
            finished: true,
            succeeded: false,
            error: action.error
          })),
          alerts: [BLAST_ALERT_ERROR],
          isSubmitting: false
        }
      }
    },
    [clearBlastAlert as any]: (state, action) => {
      const index = action.payload
      const alerts = isNumber(index)
        ? removeElementAtIndex(state.alerts, index)
        : state.alerts.filter(a => a.color === 'danger') // never auto-remove errors
      return {
        ...state,
        alerts
      }
    }
  },
  blastInitialState
)
