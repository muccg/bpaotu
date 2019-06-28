export const taxonomies = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']

export interface OperatorAndValue {
  value: string
  operator: 'is' | 'isnot'
}

export interface LoadableValues {
  isLoading: boolean
  options: any[]
}

export interface SelectableLoadableValues extends LoadableValues {
  isDisabled: boolean
  selected: OperatorAndValue
}

export interface GalaxySubmission {
  submissionId?: string
  userCreated?: boolean
  historyId?: string
  finished: boolean
  succeeded: boolean
  error?: string
}

export interface BlastSubmission {
  submissionId: string
  finished: boolean
  succeeded: boolean
  error?: string
}

export interface Alert {
  color: string
  text: string
}

export interface PageState {
  filters: {
    selectedAmplicon: OperatorAndValue
    taxonomy: {
      kingdom: SelectableLoadableValues
      phylum: SelectableLoadableValues
      class: SelectableLoadableValues
      order: SelectableLoadableValues
      family: SelectableLoadableValues
      genus: SelectableLoadableValues
      species: SelectableLoadableValues
    }
    contextual: any // TODO
  }
  samplesMapModal: {
    isOpen: boolean
    isLoading: boolean
    markers: SampleMarker[]
  }
  galaxy: {
    isSubmitting: boolean
    alerts: Alert[]
    submissions: GalaxySubmission[]
  }
  tips: {
    alerts: Alert[]
  }
  results: {
    isLoading: boolean
    errors: string[]
    data: any[]
    page: number
    pageSize: number
    rowsCount: number
    sorted: any[]
  }
}

export interface SampleMarker {
  title: string
  lat: number
  lng: number
}

export const EmptyOperatorAndValue: OperatorAndValue = { value: '', operator: 'is' }
export const EmptyLoadableValues: LoadableValues = { isLoading: null, options: [] }
export const EmptySelectableLoadableValues: SelectableLoadableValues = {
  selected: EmptyOperatorAndValue,
  isDisabled: true,
  isLoading: false,
  options: []
}

export const searchPageInitialState: PageState = {
  filters: {
    selectedAmplicon: EmptyOperatorAndValue,
    taxonomy: {
      kingdom: EmptySelectableLoadableValues,
      phylum: EmptySelectableLoadableValues,
      class: EmptySelectableLoadableValues,
      order: EmptySelectableLoadableValues,
      family: EmptySelectableLoadableValues,
      genus: EmptySelectableLoadableValues,
      species: EmptySelectableLoadableValues
    },
    contextual: {
      dataDefinitions: {
        isLoading: false,
        environment: [],
        filters: []
      },
      selectedEnvironment: EmptyOperatorAndValue,
      filtersMode: 'and',
      filters: []
    }
  },
  samplesMapModal: {
    isOpen: false,
    isLoading: false,
    markers: []
  },
  galaxy: {
    alerts: [],
    isSubmitting: false,
    submissions: []
  },
  tips: {
    alerts: [],
  },
  results: {
    isLoading: false,
    errors: [],
    data: [],
    page: 0,
    pageSize: 10,
    rowsCount: 0,
    sorted: []
  }
}

export class ErrorList extends Error {
  public msgs: string[]
  constructor(...msgs) {
    super(msgs.join('\n'))
    this.msgs = msgs
  }
}
