import { partialRight } from 'lodash'

export function handleAPIResponse(apiFn, handlerFn) {
  apiFn()
    .then(handlerFn)
    .catch(handlerFn)
}

export function handleSimpleAPIResponse(dispatch, apiFn, handlerFn) {
  return handleAPIResponse(apiFn, simpleDispatch(dispatch, handlerFn))
}

export function simpleDispatch(dispatch, action) {
  return dataOrError => {
    dispatch(action(dataOrError))
  }
}

export function changeElementAtIndex(arr, idx, fn) {
  const changedElement = fn(arr[idx])
  if (arr[idx] === changedElement) {
    return arr
  }
  let result = arr.slice(0, idx)
  if (changedElement) {
    result.push(changedElement)
  }
  result = result.concat(arr.slice(idx + 1))
  return result
}

export const removeElementAtIndex = partialRight(changeElementAtIndex, () => null)
