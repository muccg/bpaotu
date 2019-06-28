import { filter as _filter, get as _get, isArray } from 'lodash'
import * as React from 'react'
import { Col, Input, Row } from 'reactstrap'

import { ContextualDropDown } from './contextual_drop_down'

const TypeToOperatorAndValue = {
  string: StringOperatorAndValue,
  float: BetweenOperatorAndValue,
  date: BetweenOperatorAndValue,
  ontology: DropDownOperatorAndValue,
  sample_id: DropDownOperatorAndValue
}

export default class ContextualFilter extends ContextualDropDown {
  protected dropDownSize = 3

  protected renderOperatorAndValue() {
    const type = _get(this.props, 'dataDefinition.type')
    const TypeBasedOperatorAndValue = TypeToOperatorAndValue[type]

    return (
      <Col sm={8}>
        {TypeBasedOperatorAndValue ? (
          <TypeBasedOperatorAndValue
            filter={this.props.filter}
            dataDefinition={this.props.dataDefinition}
            changeOperator={op => this.props.changeOperator(this.props.index, op)}
            changeValue={value => this.props.changeValue(this.props.index, value)}
            changeValue2={value => this.props.changeValue2(this.props.index, value)}
            changeValues={value => this.props.changeValues(this.props.index, value)}
          />
        ) : null}
      </Col>
    )
  }
}

function forTargetValue(f) {
  return evt => f(evt.target.value)
}

function StringOperatorAndValue({ filter, dataDefinition, changeOperator, changeValue }) {
  return (
    <Row>
      <Col sm={4} className="no-padding-right">
        <Input type="select" value={filter.operator} onChange={forTargetValue(changeOperator)}>
          <option value="">contains</option>
          <option value="complement">doesn't contain</option>
        </Input>
      </Col>
      <Col sm={8} className="no-padding-right">
        <Input value={filter.value} onChange={forTargetValue(changeValue)} />
      </Col>
    </Row>
  )
}

function BetweenOperatorAndValue({ filter, dataDefinition, changeOperator, changeValue, changeValue2 }) {
  const valueType = dataDefinition.type === 'date' ? 'date' : 'number'
  const sizes = {
    date: { op: 2, values: 5 },
    number: { op: 4, values: 4 }
  }
  return (
    <Row>
      <Col sm={sizes[valueType].op} className="no-padding-right">
        <Input type="select" value={filter.operator} onChange={forTargetValue(changeOperator)}>
          <option value="">between</option>
          <option value="complement">not between</option>
        </Input>
      </Col>
      <Col sm={sizes[valueType].values} className="no-padding-right">
        <Input type={valueType} value={filter.value} onChange={forTargetValue(changeValue)} />
      </Col>
      <Col sm={sizes[valueType].values} className="no-padding-right">
        <Input type={valueType} value={filter.value2} onChange={forTargetValue(changeValue2)} />
      </Col>
    </Row>
  )
}

function DropDownOperatorAndValue({ filter, dataDefinition, changeOperator, changeValue, changeValues }) {
  const renderOptions = dataDefinition.values.map(value => {
    // The values are list of tuples [id, text] in general.
    // But for Sample ID the values are a list of the sample ids.
    const toIdAndText = v => {
      if (!isArray(v)) {
        // When single value (instead of [id, text]) make that both the id and the text
        return [v, v]
      }
      const [idx, txt] = v
      if (idx === 0 && txt === '') {
        // Make the "no selection" value the empty string for consistency with other contextual filter types
        return ['', '']
      }
      return [idx, txt]
    }

    const [id, text] = toIdAndText(value)
    return (
      <option key={id} value={id}>
        {text}
      </option>
    )
  })

  const isMultiSelect = dataDefinition.type === 'sample_id'

  const onChange = evt => {
    if (isMultiSelect) {
      const values = _filter(evt.target.options, o => o.selected).map((o: any) => o.value)
      changeValues(values)
    } else {
      changeValue(evt.target.value)
    }
  }

  return (
    <Row>
      <Col sm={4} className="no-padding-right">
        <Input type="select" value={filter.operator} onChange={forTargetValue(changeOperator)}>
          <option value="">is</option>
          <option value="complement">isn't</option>
        </Input>
      </Col>
      <Col sm={8} className="no-padding-right">
        <Input
          type="select"
          multiple={isMultiSelect}
          value={isMultiSelect ? filter.values : filter.value}
          onChange={onChange}
        >
          {renderOptions}
        </Input>
      </Col>
    </Row>
  )
}
