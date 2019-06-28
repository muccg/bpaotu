import { get as _get } from 'lodash'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { selectAmplicon, selectAmpliconOperator } from '../reducers/amplicon'
import { updateTaxonomyDropDowns } from '../reducers/taxonomy'

import DropDownFilter from '../../../components/drop_down_filter'

function mapStateToProps(state) {
  return {
    label: 'Amplicon',
    options: state.referenceData.amplicons.values,
    optionsLoadingError: state.referenceData.amplicons.error,
    isDisabled: _get(state, 'referenceData.amplicons.values', []).length === 0,
    optionsLoading: state.referenceData.amplicons.isLoading,
    selected: state.searchPage.filters.selectedAmplicon
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      selectValue: selectAmplicon,
      selectOperator: selectAmpliconOperator,
      onChange: updateTaxonomyDropDowns('')
    },
    dispatch
  )
}

const AmpliconFilter = connect(
  mapStateToProps,
  mapDispatchToProps
)(DropDownFilter)

export default AmpliconFilter
