
### webviz-subsurface package

?> :bookmark: This documentation is valid for version `0.2.11` of `webviz-subsurface`.



---

<div class="plugin-doc">

#### SimulationTimeSeries

> :warning: At least one argument has a deprecation warning.</summary>


<!-- tabs:start -->


<!-- tab:Arguments -->










>:warning: **`options`:** Certain values for the argument have been deprecated and might soon not be accepted anymore. See function below for details.











---



Function checking for deprecations:
```python
def check_deprecation_argument(options: Optional[dict]) -> Optional[Tuple[str, str]]:
    if options is None:
        return None
    if any(elm in options for elm in ["vector1", "vector2", "vector3"]):
        return (
            'The usage of "vector1", "vector2" and "vector3" as user input options are deprecated. '
            'Please replace options with list named "vectors"',
            'The usage of "vector1", "vector2" and "vector3" as user input in options for '
            "initially selected vectors are deprecated. Please replace user input options with "
            'list named "vectors", where each element represent the corresponding initially '
            "selected vector.",
        )
    return None

```
---

---
How to use in YAML config file:
```yaml
    - SimulationTimeSeries:
        ensembles:  # Optional, type Union[list, NoneType].
        rel_file_pattern:  # Optional, type str.
        perform_presampling:  # Optional, type bool.
        obsfile:  # Optional, type str (corresponding to a path).
        options:  # Deprecated, type dict.
        sampling:  # Optional, type str.
        predefined_expressions:  # Optional, type str.
        user_defined_vector_definitions:  # Optional, type str.
        line_shape_fallback:  # Optional, type str.
```



<!-- tabs:end -->

</div>


