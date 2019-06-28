import { last } from 'lodash'
import * as React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Alert, Button, Card, CardBody, CardFooter, CardHeader, Col, Container, Input, Row } from 'reactstrap'

import Octicon from '../../../components/octicon'
import LoadingSpinner from '../../../components/search_spinner'
import { clearBlastAlert, handleBlastSequence, runBlast } from '../reducers/blast_search'

export class BlastSearchCard extends React.Component<any> {
  public render() {
    const wrapText = text => ({ __html: text })
    return (
      <Card>
        <CardHeader tag="h5">BLAST Search</CardHeader>
        <CardBody className="blast">
          <Input
            type="textarea"
            name="sequence"
            id="sequence"
            placeholder="Select Amplicon and enter sequence here to run BLAST"
            value={this.props.sequenceValue}
            disabled={!this.props.isAmpliconSelected}
            onChange={evt => this.props.handleBlastSequence(evt.target.value)}
          />
          <div className="pt-2">
            {this.props.alerts.map((alert, idx) => (
              <Alert
                key={idx}
                color={alert.color}
                className="text-center"
                toggle={() => this.props.clearBlastAlert(idx)}
              >
                <div dangerouslySetInnerHTML={wrapText(alert.text)} />
              </Alert>
            ))}
          </div>
        </CardBody>
        <CardFooter className="text-center">
          {this.props.isSubmitting && <LoadingSpinner />}

          <Button color="warning" disabled={this.props.isSearchDisabled} onClick={this.props.runBlast}>
            Run BLAST
          </Button>
        </CardFooter>
      </Card>
    )
  }
}

function mapStateToProps(state, props) {
  return {
    isAmpliconSelected: state.searchPage.filters.selectedAmplicon.value,
    sequenceValue: state.searchPage.blastSearch.sequenceValue,
    isSubmitting: state.searchPage.blastSearch.isSubmitting,
    isSearchDisabled:
      state.searchPage.filters.selectedAmplicon.value === '' ||
      state.searchPage.blastSearch.sequenceValue === '' ||
      state.searchPage.blastSearch.isSubmitting,
    alerts: state.searchPage.blastSearch.alerts
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      handleBlastSequence,
      runBlast,
      clearBlastAlert
    },
    dispatch
  )
}
export default connect(
  mapStateToProps,
  mapDispatchToProps
)(BlastSearchCard)
