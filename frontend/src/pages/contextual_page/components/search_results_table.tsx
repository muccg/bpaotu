import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import 'react-table/react-table.css'

import { fieldsToColumns, SearchResultsTable } from '../../../components/search_results_table'
import { changeTableProperties, search } from '../reducers/search'

function mapStateToProps(state) {
  return {
    results: state.contextualPage.results,
    extraColumns: fieldsToColumns(state.contextualPage.selectColumns.columns)
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
