window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        update_figure: function (data, layout) {
            return { 'data': data, 'layout': layout }
        }
    }
});
