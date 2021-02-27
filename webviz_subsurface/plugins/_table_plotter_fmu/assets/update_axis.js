
window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        update_figure: function (figure, x_scale, y_scale) {
            let { data, layout } = figure
            let { xaxis, yaxis } = layout
            xaxis = { ...xaxis, 'type': x_scale }
            yaxis = { ...yaxis, 'type': y_scale }

            return {
                'data': data,
                'layout': {
                    ...layout, xaxis, yaxis
                }
            }
        }
    }
});
