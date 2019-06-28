import { concat, map } from 'lodash'
import * as React from 'react'
import { Col, FormGroup, Input, Label } from 'reactstrap'
import { OperatorAndValue } from '../pages/search_page/reducers/types'

interface Props {
  label: string
  selected: OperatorAndValue
  optionsLoading: boolean
  options: OperatorAndValue[]
  selectValue: (id: string) => void
  selectOperator: (id: string) => void
  onChange: (id: string) => void
}

export default class DropDownFilter extends React.Component<any> {
  constructor(props) {
    super(props)
    this.onOperatorChange = this.onOperatorChange.bind(this)
    this.onValueChange = this.onValueChange.bind(this)
  }

  public render() {
    return (
      <FormGroup row={true}>
        <Label sm={3}>{this.props.label}</Label>
        <Col sm={3}>
          <Input
            type="select"
            name="operator"
            disabled={this.props.isDisabled}
            value={this.props.selected.operator}
            onChange={this.onOperatorChange}
          >
            <option value="is">is</option>
            <option value="isnot">isn't</option>
          </Input>
        </Col>
        <Col sm={6}>
          <Input
            type="select"
            name="value"
            invalid={this.props.optionsLoadingError}
            disabled={this.props.isDisabled || this.props.optionsLoadingError}
            value={this.props.selected.value}
            onChange={this.onValueChange}
          >
            {this.renderOptions()}
          </Input>
        </Col>
      </FormGroup>
    )
  }

  public renderOptions() {
    if (this.props.optionsLoadingError) {
      return (
        <option key="error" value="">
          Couldn't load values!
        </option>
      )
    }
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
    return (
      <option key={option.id} value={option.id}>
        {option.value}
      </option>
    )
  }

  public onValueChange(evt) {
    const id = evt.target.value
    this.props.selectValue(id)
    if (this.props.onChange) {
      this.props.onChange()
    }
  }

  public onOperatorChange(evt: any) {
    const value = evt.target.value
    this.props.selectOperator(value)
    if (this.props.onChange) {
      this.props.onChange()
    }
  }
}
