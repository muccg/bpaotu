import * as React from 'react'

import { Button } from 'reactstrap'

import Octicon from './octicon'

export default props => (
  <Button block={true} color="primary" size="lg" disabled={props.isDisabled} onClick={props.search}>
    <Octicon name="search" /> &nbsp; Search
  </Button>
)
