import * as React from 'react'
import { Alert, Container } from 'reactstrap'

export default props => {
  const ckanURL = path => `${window.otu_search_config.ckan_base_url}/${path}`

  return (
    <Container fluid={true}>
      <Alert color="danger" className="text-center">
        <h4 className="alert-heading">Australian Microbiome Data Access Required</h4>
        <p>You do not have access to the Australian Microbiome data.</p>
        <p>
          Please contact <a href="mailto:help@bioplatforms.com">support</a>.
        </p>
      </Alert>
    </Container>
  )
}
