import { filter, find } from 'lodash'
import * as React from 'react'
import { connect } from 'react-redux'
import { Button, Card, CardBody, CardFooter, CardHeader, Col, Form, Input, Row } from 'reactstrap'
import { bindActionCreators } from 'redux'
import {
  addContextualFilter,
  changeContextualFilterOperator,
  changeContextualFilterValue,
  changeContextualFilterValue2,
  changeContextualFilterValues,
  clearContextualFilters,
  doesFilterMatchEnvironment,
  removeContextualFilter,
  selectContextualFilter,
  selectContextualFiltersMode
} from '../reducers/contextual'
import { fetchContextualDataDefinitions } from '../reducers/contextual_data_definitions'

import ContextualFilter from '../../../components/contextual_filter'
import Octicon from '../../../components/octicon'
import EnvironmentFilter from './environment_filter'

class ContextualFilterCard extends React.Component<any> {
  public componentDidMount() {
    this.props.fetchContextualDataDefinitions()
  }

  public render() {
    return (
      <Card>
        <CardHeader>
          Contextual Filters
        </CardHeader>
        <CardBody className="filters">
          <EnvironmentFilter />

          <hr />
          <h5 className="text-center">Contextual Filters</h5>

          <Row>
            <Col>
              <p className="text-center">
                Contextual filters allow data to be filtered on site specific chemical and physical data. More than one filter may be used and combined with "all/any" functions.
              </p>
            </Col>
          </Row>

          {this.props.contextualFilters.length >= 2 && (
            <Row>
              <Col sm={12}>
                <Form inline={true}>
                  Samples must match &nbsp;
                  <Input
                    type="select"
                    bsSize="sm"
                    value={this.props.contextualFiltersMode}
                    onChange={evt => this.props.selectContextualFiltersMode(evt.target.value)}
                  >
                    <option value="and">all</option>
                    <option value="or">any</option>
                  </Input>
                  &nbsp; of the following contextual filters.
                </Form>
              </Col>
            </Row>
          )}

          <Row className="space-above" />

          {this.props.contextualFilters.map((fltr, index) => (
            <ContextualFilter
              key={`${fltr.name}-${index}`}
              index={index}
              filter={fltr}
              dataDefinition={find(this.props.dataDefinitions, dd => dd.name === fltr.name)}
              options={this.props.contextualFilterOptions}
              optionsLoading={this.props.optionsLoading}
              remove={this.props.removeContextualFilter}
              select={this.props.selectContextualFilter}
              changeOperator={this.props.changeContextualFilterOperator}
              changeValue={this.props.changeContextualFilterValue}
              changeValue2={this.props.changeContextualFilterValue2}
              changeValues={this.props.changeContextualFilterValues}
            />
          ))}
        </CardBody>
        <CardFooter className="text-center">
          <Button color="success" onClick={this.props.addContextualFilter}>
            Add
          </Button>
          <Button color="warning" onClick={this.props.clearContextualFilters}>
            Clear
          </Button>
        </CardFooter>
      </Card>
    )
  }
}

const getFilterOptions = (filters, selectedEnvironment) =>
  filter(filters, doesFilterMatchEnvironment(selectedEnvironment))

function mapStateToProps(state) {
  return {
    contextualFilters: state.searchPage.filters.contextual.filters,
    contextualFiltersMode: state.searchPage.filters.contextual.filtersMode,
    dataDefinitions: state.searchPage.filters.contextual.dataDefinitions.filters,
    contextualFilterOptions: getFilterOptions(
      state.searchPage.filters.contextual.dataDefinitions.filters,
      state.searchPage.filters.contextual.selectedEnvironment
    ),
    optionsLoading: state.searchPage.filters.contextual.dataDefinitions.isLoading
  }
}

function mapDispatchToProps(dispatch: any) {
  return bindActionCreators(
    {
      fetchContextualDataDefinitions,
      selectContextualFiltersMode,
      addContextualFilter,
      removeContextualFilter,
      selectContextualFilter,
      changeContextualFilterOperator,
      changeContextualFilterValue,
      changeContextualFilterValue2,
      changeContextualFilterValues,
      clearContextualFilters
    },
    dispatch
  )
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ContextualFilterCard)
