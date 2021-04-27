window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        update_figure: function (layout, data) {
            return { 'data': data, 'layout': layout }
        }
    }
});
