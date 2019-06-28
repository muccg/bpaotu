import { capitalize, concat, drop, first, get as _get, isEmpty, join, map, reject } from 'lodash'
import * as React from 'react'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import ReactTable from 'react-table'
import 'react-table/react-table.css'

export class SearchResultsTable extends React.Component<any> {
  public defaultColumns = [
    {
      Header: 'Sample ID',
      accessor: 'sample_id',
      sortable: true,
      Cell: row => (
        <div>
          <a href={bpaIDToCKANURL(row.value)} target="_blank">
            {row.value}
          </a>
        </div>
      )
    },
    {
      Header: 'Environment',
      sortable: true,
      accessor: 'environment'
    }
  ]

  constructor(props) {
    super(props)
    this.onSortedChange = this.onSortedChange.bind(this)
    this.onPageChange = this.onPageChange.bind(this)
    this.onPageSizeChange = this.onPageSizeChange.bind(this)
  }

  public componentDidMount() {
    if (isEmpty(this.props.results.data)) {
      this.props.search()
    }
  }

  public getColumns() {
    const extraColumns = map(this.props.extraColumns, field => ({
      Header: _get(field, 'displayName', field.name),
      accessor: field.name,
      sortable: _get(field, 'sortable', true)
    }))
    const columns = this.defaultColumns.concat(extraColumns)
    return columns
  }

  public render() {
    return (
      <div>
        <ReactTable
          columns={this.getColumns()}
          manual={true}
          loading={this.props.results.isLoading}
          data={this.props.results.data}
          page={this.props.results.page}
          pageSize={this.props.results.pageSize}
          pages={this.props.results.pages}
          className="-striped -highlight"
          onSortedChange={this.onSortedChange}
          onPageChange={this.onPageChange}
          onPageSizeChange={this.onPageSizeChange}
        />
      </div>
    )
  }

  public onPageChange(pageIndex) {
    this.props.changeTableProperties({
      ...this.props.results,
      page: pageIndex
    })
    this.props.search()
  }

  public onPageSizeChange(pageSize) {
    this.props.changeTableProperties({
      ...this.props.results,
      pageSize
    })
    this.props.search()
  }

  public onSortedChange(sorted) {
    this.props.changeTableProperties({
      ...this.props.results,
      sorted
    })
    this.props.search()
  }
}

function bpaIDToCKANURL(bpaId) {
  return `${window.otu_search_config.ckan_base_url}/organization/australian-microbiome?q=sample_id:102.100.100/${bpaId}`
}

function fieldToDisplayName(fieldName) {
  const words = fieldName.split('_')
  // For ontology foreign key cases, we drop all 'id' words that are not in the first position
  const filteredWords = concat([first(words)], reject(drop(words), w => w === 'id'))
  const userFriendly = join(map(filteredWords, capitalize), ' ')
  return userFriendly
}

export const fieldsToColumns = fields =>
  map(reject(fields, f => isEmpty(f.name)), c => ({
    name: c.name,
    displayName: fieldToDisplayName(c.name)
  }))
