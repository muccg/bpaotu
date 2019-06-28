import * as React from 'react'

import { Alert } from 'reactstrap'

export default ({ errors }) => {
  if (errors.length === 0) {
    return <span />
  }
  return (
    <Alert color="danger">
      <h4 className="alert-heading">Errors</h4>
      <ul>
        {errors.map((err, idx) => (
          <li key={idx}>{err}</li>
        ))}
      </ul>
    </Alert>
  )
}
