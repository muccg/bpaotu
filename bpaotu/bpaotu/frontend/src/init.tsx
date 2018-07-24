import 'bootstrap/dist/css/bootstrap.min.css';

import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import thunk from 'redux-thunk';
import { createStore, applyMiddleware } from 'redux';
import { BrowserRouter as Router} from 'react-router-dom';

import App from './app';
import reducers from './reducers'

export const store = createStore(
    reducers,
    applyMiddleware(thunk)
);

ReactDOM.render(
    <Provider store={store}>
        <Router basename={window.otu_search_config.base_url}>
            <App />
        </Router>
    </Provider>,
    document.getElementById('app'));