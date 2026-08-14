(function () {
  function applyPatch() {
    var ns = window.webviz_core_components;
    var React = window.React;

    if (!ns || !React || typeof ns.WebvizSettings !== "function") {
      return false;
    }

    if (ns.WebvizSettings.__dash3CompatPatched) {
      return true;
    }

    var PatchedWebvizSettings = function (props) {
      var style = {
        opacity: props && props.visible ? 1 : 0,
        width: props && props.width,
        pointerEvents: props && props.visible ? "all" : "none",
      };

      // Dash 3 no longer provides the private _dashprivate_layout prop expected
      // by older webviz-core-components. Rendering children directly avoids the
      // crash while keeping the settings drawer usable.
      return React.createElement(
        "div",
        { className: "WebvizSettings", style: style },
        props ? props.children : null
      );
    };

    PatchedWebvizSettings.__dash3CompatPatched = true;
    PatchedWebvizSettings.displayName = "WebvizSettingsDash3Compat";
    PatchedWebvizSettings.propTypes = ns.WebvizSettings.propTypes;
    PatchedWebvizSettings.defaultProps = ns.WebvizSettings.defaultProps;

    ns.WebvizSettings = PatchedWebvizSettings;
    return true;
  }

  if (!applyPatch()) {
    window.addEventListener("load", applyPatch, { once: true });
  }
})();
