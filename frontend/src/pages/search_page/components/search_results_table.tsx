import { isEmpty, reject, uniqBy } from 'lodash'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import 'react-table/react-table.css'

import { fieldsToColumns, SearchResultsTable } from '../../../components/search_results_table'
import { changeTableProperties, search } from '../reducers/search'

function mapStateToProps(state) {
  const nonEmptyFilters = uniqBy(reject(state.searchPage.filters.contextual.filters, f => isEmpty(f.name)), 'name')
  return {
    results: state.searchPage.results,
    extraColumns: fieldsToColumns(nonEmptyFilters)
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      changeTableProperties,
      search
    },
    dispatch
  )
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SearchResultsTable)
