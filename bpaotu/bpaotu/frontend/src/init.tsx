import 'bootstrap/dist/css/bootstrap.min.css';

import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import thunk from 'redux-thunk';
import { createStore, applyMiddleware } from 'redux';
import { BrowserRouter as Router} from 'react-router-dom';

import App from './app/index';
import reducers from './reducers'

export const store = createStore(
    reducers,
    applyMiddleware(thunk)
);

ReactDOM.render(
    <Provider store={store}>
        <Router basename={window.location.pathname}>
            <App />
        </Router>
    </Provider>,
    document.getElementById('app'));