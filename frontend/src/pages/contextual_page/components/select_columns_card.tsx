import { find, partial } from 'lodash'
import * as React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Button, Card, CardBody, CardFooter, CardHeader } from 'reactstrap'

import { ContextualDropDown } from '../../../components/contextual_drop_down'

import { fetchColumnsDataDefinitions } from '../reducers/columns_data_definitions'
import { search } from '../reducers/search'
import { addColumn, clearColumns, removeColumn, selectColumn } from '../reducers/select_columns'

class SelectColumnsCard extends React.Component<any> {
  constructor(props) {
    super(props)
    this.onRemoveColumn = this.onRemoveColumn.bind(this)
    this.onSelectColumn = this.onSelectColumn.bind(this)
    this.onClearColumns = this.onClearColumns.bind(this)
  }

  public componentDidMount() {
    this.props.fetchColumnsDataDefinitions()
  }

  public render() {
    return (
      <Card>
        <CardHeader>Select Columns</CardHeader>
        <CardBody className="filters">
          {this.props.columns.map((column, index) => (
            <ContextualDropDown
              key={`${column.name}-${index}`}
              index={index}
              filter={column}
              dataDefinition={find(this.props.dataDefinitions, dd => dd.name === column.name)}
              options={this.props.dataDefinitions}
              optionsLoading={this.props.optionsLoading}
              remove={this.onRemoveColumn}
              select={this.onSelectColumn}
            />
          ))}
        </CardBody>
        <CardFooter className="text-center">
          <Button color="success" onClick={this.props.addColumn}>
            Add
          </Button>
          <Button color="warning" onClick={this.onClearColumns}>
            Clear
          </Button>
        </CardFooter>
      </Card>
    )
  }

  private onRemoveColumn(...args) {
    this.props.removeColumn(...args)
    this.props.search()
  }

  private onSelectColumn(...args) {
    this.props.selectColumn(...args)
    this.props.search()
  }

  private onClearColumns() {
    this.props.clearColumns()
    this.props.search()
  }
}

function mapStateToProps(state) {
  return {
    columns: state.contextualPage.selectColumns.columns,
    dataDefinitions: state.contextualPage.selectColumns.dataDefinitions.values,
    optionsLoading: state.contextualPage.selectColumns.dataDefinitions.isLoading
  }
}

function mapDispatchToProps(dispatch: any) {
  return bindActionCreators(
    {
      fetchColumnsDataDefinitions,
      addColumn,
      removeColumn,
      selectColumn,
      clearColumns,
      search
    },
    dispatch
  )
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SelectColumnsCard)
