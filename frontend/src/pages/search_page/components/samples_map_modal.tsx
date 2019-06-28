import * as React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Modal, ModalBody, ModalHeader } from 'reactstrap'

import SamplesMap from '../../../components/samples_map'
import { closeSamplesMapModal, fetchSampleMapModalSamples } from '../reducers/samples_map_modal'

const SamplesMapModal = props => (
  <Modal isOpen={props.isOpen}>
    <ModalHeader toggle={props.closeSamplesMapModal}>Sample Collection Sites</ModalHeader>
    <ModalBody>
      <SamplesMap fetchSamples={props.fetchSampleMapModalSamples} isLoading={props.isLoading} markers={props.markers} />
    </ModalBody>
  </Modal>
)

function mapStateToProps(state) {
  const { isLoading, isOpen, markers } = state.searchPage.samplesMapModal
  return {
    isLoading,
    isOpen,
    markers
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(
    {
      closeSamplesMapModal,
      fetchSampleMapModalSamples
    },
    dispatch
  )
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SamplesMapModal)
