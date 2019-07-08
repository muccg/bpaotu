import { join } from 'lodash'
import * as React from 'react'
import { Collapse, Nav, Navbar, NavbarBrand, NavbarToggler, NavItem, NavLink } from 'reactstrap'

import { Link, NavLink as RRNavLink } from 'react-router-dom'
import Octicon from '../components/octicon'

export default class Header extends React.Component<any, any> {
  constructor(props) {
    super(props)

    this.toggle = this.toggle.bind(this)
    this.state = {
      isOpen: false
    }
  }

  public toggle() {
    this.setState({
      isOpen: !this.state.isOpen
    })
  }

  public render() {
    const logoPNG = window.otu_search_config.static_base_url + join(['bpa-logos', 'bpalogo_withdataportal.png'], '/')
    return (
      <Navbar color="light" light={true} expand="lg">
        <NavbarBrand className="site-header-logo" href="https://data.bioplatforms.com/">
          <img src={logoPNG} alt="Bioplatform Australia" />
        </NavbarBrand>
        <NavbarToggler onClick={this.toggle} />
        <Collapse isOpen={this.state.isOpen} navbar={true}>
          <Nav className="navbar-nav">
            <NavItem>
              <NavLink href="https://data.bioplatforms.com/organization/about/australian-microbiome">
                Australian Microbiome Home
              </NavLink>
            </NavItem>

            <NavItem>
              <NavLink exact={true} to="/" activeClassName="active" tag={RRNavLink}>
                Search
              </NavLink>
            </NavItem>

            <NavItem>
              <NavLink to="/map" activeClassName="active" tag={RRNavLink}>
                Map
              </NavLink>
            </NavItem>

            <NavItem>
              <NavLink to="/contextual" activeClassName="active" tag={RRNavLink}>
                Contextual
              </NavLink>
            </NavItem>
          </Nav>
          <Nav className="ml-auto" navbar={true}>
            <NavItem>
              {this.props.userEmailAddress ? (
                <div>
                  <Octicon name="person" />
                  <span className="site-header-username">{this.props.userEmailAddress}</span>
                </div>
              ) : (
                ''
              )}
            </NavItem>
          </Nav>
        </Collapse>
      </Navbar>
    )
  }
}
