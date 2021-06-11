window.dash_clientside = Object.assign({}, window.dash_clientside, {
  clientside: {
    set_dcc_figure: function (layout, data) {
      /*
        Can be used in a dash callback to update
        the `figure` prop on a dcc.Graph component,
        e.g. to update the `layout` clientside without
        sending the `data` from the backend.
      */
      return { data: data, layout: layout };
    },
    get_client_height: function (_triggered) {
      /*
          Can be used in a dash callback to get the clientHeight
          in pixels
     */
      return document.documentElement.clientHeight
    }
  },
});
