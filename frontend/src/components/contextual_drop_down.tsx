import { concat, map } from 'lodash'
import * as React from 'react'
import { Button, Col, Input, Row } from 'reactstrap'
import Octicon from './octicon'

export class ContextualDropDown extends React.Component<any> {
  protected dropDownSize = 11

  public render() {
    return (
      <Row>
        <Col sm={1} className="no-padding-right">
          <Button
            outline={true}
            color="warning"
            size="sm"
            className="form-control"
            onClick={() => this.props.remove(this.props.index)}
          >
            <Octicon name="dash" size="small" />
          </Button>
        </Col>
        <Col sm={this.dropDownSize} className="no-padding-right">
          <Input
            type="select"
            value={this.props.filter.name}
            onChange={evt => this.props.select(this.props.index, evt.target.value)}
          >
            {this.renderOptions()}
          </Input>
        </Col>
        {this.renderOperatorAndValue()}
      </Row>
    )
  }

  public renderOptions() {
    if (this.props.optionsLoading) {
      return (
        <option key="loading" value="">
          Loading...
        </option>
      )
    }
    return concat(
      [
        <option key="" value="">
          ---
        </option>
      ],
      map(this.props.options, this.renderOption)
    )
  }

  public renderOption(option) {
    let displayName = option.display_name
    if (option.units) {
      displayName += ` [${option.units}]`
    }
    return (
      <option key={option.name} value={option.name}>
        {displayName}
      </option>
    )
  }

  protected renderOperatorAndValue() {
    return <span />
  }
}
