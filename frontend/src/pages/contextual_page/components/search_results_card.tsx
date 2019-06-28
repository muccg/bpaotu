import { isEmpty, map, reject } from 'lodash'
import * as React from 'react'
import { connect } from 'react-redux'

import { Button, Card, CardBody, CardHeader } from 'reactstrap'

import Octicon from '../../../components/octicon'

import { EmptyOTUQuery } from '../../../search'
import SearchResultsTable from './search_results_table'

const HeaderButton = props => (
  <Button style={{ marginRight: 10 }} outline={true} color="primary" disabled={props.disabled} onClick={props.onClick}>
    {props.octicon ? (
      <span>
        <Octicon name={props.octicon} />
        &nbsp;
      </span>
    ) : (
      ''
    )}
    {props.text}
  </Button>
)

class SearchResultsCard extends React.Component<any, any> {
  constructor(props) {
    super(props)
    this.exportCSV = this.exportCSV.bind(this)
  }

  public render() {
    return (
      <div>
        <Card>
          <CardHeader>
            <div>
              <HeaderButton octicon="desktop-download" text="Export Search Results (CSV)" onClick={this.exportCSV} />
            </div>
          </CardHeader>
          <CardBody>
            <SearchResultsTable />
          </CardBody>
        </Card>
      </div>
    )
  }

  public exportCSV() {
    const params = new URLSearchParams()
    params.set('token', this.props.ckanAuthToken)
    params.set('otu_query', JSON.stringify(EmptyOTUQuery))
    params.set('columns', JSON.stringify(this.props.extraColumns))
    params.set('sorting', JSON.stringify(this.props.sorting))

    const baseURL = window.otu_search_config.contextual_csv_download_endpoint
    const url = `${baseURL}?${params.toString()}`
    window.open(url)
  }
}

function mapStateToProps(state) {
  return {
    ckanAuthToken: state.auth.ckanAuthToken,
    extraColumns: reject(map(state.contextualPage.selectColumns.columns, c => c.name), c => isEmpty(c)),
    sorting: state.contextualPage.results.sorted
  }
}

export default connect(
  mapStateToProps,
  null
)(SearchResultsCard)
