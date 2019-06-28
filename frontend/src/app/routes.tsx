import * as React from 'react'
import { Route, Switch } from 'react-router-dom'

import ContextualPage from '../pages/contextual_page'
import MapPage from '../pages/map_page'
import SearchPage from '../pages/search_page'

export default _ => (
  <div>
    <Switch>
      <Route exact={true} path="/" component={SearchPage} />
      <Route path="/map" component={MapPage} />
      <Route path="/contextual" component={ContextualPage} />
    </Switch>
  </div>
)
