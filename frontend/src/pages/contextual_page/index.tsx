import * as React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Col, Container, Row } from 'reactstrap'

import SearchResultsCard from './components/search_results_card'
import SelectColumnsCard from './components/select_columns_card'

import { search } from './reducers/search'

export const ContextualPage = props => (
  <Container fluid={true}>
    <Row className="space-above">
      <Col sm={{ size: 6, offset: 3 }}>
        <SelectColumnsCard />
      </Col>
    </Row>

    {/* The Search button is need as we search on each modification.
            Uncomment, if you want the Search button as well.
        <Row className="space-above">
            <Col sm={{ size: 2, offset: 5 }}>
                <SearchButton
                    isDisabled={props.isSearchButtonDisabled}
                    search={props.search} />
            </Col>
        </Row>
        */}

    <Row className="space-above">
      <Col sm={12}>
        <SearchResultsCard />
      </Col>
    </Row>
  </Container>
)

function mapStateToProps(state) {
  return {
    isSearchButtonDisabled: state.searchPage.results.isLoading,
    errors: state.searchPage.results.errors
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      search
    },
    dispatch
  )
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ContextualPage)
