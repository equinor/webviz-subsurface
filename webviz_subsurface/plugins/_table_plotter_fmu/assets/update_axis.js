window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        update_figure: function (figure, options) {

            ///Get triggered input, deserialize and retrieve attribute
            let triggered = dash_clientside.callback_context.triggered[0]['prop_id']
            triggered = triggered.substring(0, triggered.lastIndexOf('.'))
            triggered = JSON.parse(triggered)["plotly_attribute"]
            let value = dash_clientside.callback_context.triggered[0]["value"]

            //Return as is if input is the figure from store
            if (triggered === 'figure') {
                return figure
            }
            //Update property using lodash
            let fig = _.clone(figure)
            fig = _.set(fig, triggered, value)
            return fig
        }
    }
});
