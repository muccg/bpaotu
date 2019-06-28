import * as octicons from 'octicons'
import * as React from 'react'

const style = {
  display: 'inline-block',
  verticalAlign: 'middle',
  paddingTop: 8
}

export default props => {
  const Sizes = {
    small: 12,
    large: 32,
    larger: 48
  }
  const width = Sizes[props.size] || 20

  const options = { width, height: width }
  return <div style={style} dangerouslySetInnerHTML={{ __html: octicons[props.name].toSVG(options) }} />
}
