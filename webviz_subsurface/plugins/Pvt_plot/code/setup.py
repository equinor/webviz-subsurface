from setuptools import setup, find_packages


TESTS_REQUIRE = ["selenium~=3.141", "pylint", "mock", "black", "bandit"]

setup(
    name="webviz_wlf_tutorial",
    description="Webviz Layout Framework Tutorial",
    # long_description=LONG_DESCRIPTION,
    # long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests"]),
    entry_points={
        "webviz_config_plugins": [
            # add new lines to add new plugins
            "PvtPlotter = _new_pvt_plot:PvtPlotter",
        ]
    },
    install_requires=[
        "webviz-config>=0.1.0",
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
    python_requires="~=3.6",
    use_scm_version=False,
    zip_safe=False,
    classifiers=[
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Framework :: Dash",
        "Framework :: Flask",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)