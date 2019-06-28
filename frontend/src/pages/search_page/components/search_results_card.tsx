import { last } from 'lodash'
import * as React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Alert, Button, Card, CardBody, CardHeader } from 'reactstrap'

import Octicon from '../../../components/octicon'
import { openSamplesMapModal } from '../reducers/samples_map_modal'
import { describeSearch } from '../reducers/search'
import { clearGalaxyAlert, submitToGalaxy, workflowOnGalaxy } from '../reducers/submit_to_galaxy'
import { clearTips, showPhinchTip } from '../reducers/tips'
import { GalaxySubmission } from '../reducers/types'
import SamplesMapModal from './samples_map_modal'
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
    this.exportBIOM = this.exportBIOM.bind(this)
  }

  public render() {
    /*
        TODO
        The UI for the galaxy submission will probably change, so showing the history link inside the Alert box might not
        be necessary later on.
        In case, we keep this code, we should probably use something like sanitize-html to make sure we don't end up with
        anything dangerous in the text.
        */
    const wrapText = text => ({ __html: text })
    return (
      <div>
        <Card>
          <CardHeader>
            <div>
              <HeaderButton octicon="globe" text="Show results on Map" onClick={this.props.openSamplesMapModal} />
              {window.otu_search_config.galaxy_integration && (
                <HeaderButton
                  octicon="clippy"
                  text="Export Data to Galaxy Australia for further analysis"
                  disabled={this.isGalaxySubmissionDisabled()}
                  onClick={this.props.submitToGalaxy}
                />
              )}
              {window.otu_search_config.galaxy_integration && (
                <HeaderButton
                  octicon="graph"
                  text="Make Krona Taxonomic Abundance Graph using Galaxy Australia"
                  disabled={this.isGalaxySubmissionDisabled()}
                  onClick={this.props.workflowOnGalaxy}
                />
              )}
              <HeaderButton octicon="desktop-download" text="Export Search Results (CSV)" onClick={this.exportCSV} />
              <HeaderButton octicon="desktop-download" text="Export Search Results (Phinch compatible BIOM)" onClick={this.exportBIOM} />
            </div>
          </CardHeader>
          <CardBody>
            <div>
              {this.props.galaxy.alerts.map((alert, idx) => (
                <Alert
                  key={idx}
                  color={alert.color}
                  className="text-center"
                  toggle={() => this.props.clearGalaxyAlert(idx)}
                >
                  <div dangerouslySetInnerHTML={wrapText(alert.text)} />
                </Alert>
              ))}
            </div>
            <div>
              {this.props.tips.alerts.map((alert, idx) => (
                <Alert
                  key={idx}
                  color={alert.color}
                  className="text-center"
                  toggle={() => this.props.clearTips(idx)}
                >
                  <div dangerouslySetInnerHTML={wrapText(alert.text)} />
                </Alert>
              ))}
            </div>
            <SearchResultsTable />
          </CardBody>
        </Card>
        <SamplesMapModal />
      </div>
    )
  }

  public isGalaxySubmissionDisabled() {
    if (this.props.galaxy.isSubmitting) {
      return true
    }
    const lastSubmission: GalaxySubmission = last(this.props.galaxy.submissions)
    return lastSubmission && !lastSubmission.finished
  }

  public export(baseURL) {
    const params = new URLSearchParams()
    params.set('token', this.props.ckanAuthToken)
    params.set('q', JSON.stringify(describeSearch(this.props.filters)))

    const url = `${baseURL}?${params.toString()}`
    window.open(url)
  }

  public exportBIOM() {
    this.props.showPhinchTip();
    this.export(window.otu_search_config.export_biom_endpoint)
  }

  public exportCSV() {
    this.export(window.otu_search_config.export_endpoint)
  }
}

function mapStateToProps(state) {
  return {
    ckanAuthToken: state.auth.ckanAuthToken,
    galaxy: state.searchPage.galaxy,
    tips: state.searchPage.tips,
    filters: state.searchPage.filters
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      openSamplesMapModal,
      submitToGalaxy,
      workflowOnGalaxy,
      clearGalaxyAlert,
      clearTips,
      showPhinchTip,
    },
    dispatch
  )
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SearchResultsCard)
