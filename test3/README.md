This webviz instance has been automatically created from configuration file.

## Run locally

You can run it locally with:

  cd THISFOLDER
  python ./webviz_app.py

## Upload and build into Azure Container registry

If you want to upload it to e.g. Azure Container Registry, you can do e.g.

  cd THISFOLDER
  az acr build --registry $ACR_NAME --image $IMAGE_NAME . 

assuming you have set the environment variables $ACR_NAME and $IMAGE_NAME.

## Private plugin projects

Note that if you have included plugins from private GitHub projects in your
application, you will need to provide a build time environment variable to Docker e.g. like:

docker build . --build-arg GITHUB_DEPLOY_KEYS=COMMA_SEPARATED_LIST_OF_DEPLOY_KEYS.

To read more on GitHub deploy keys, see https://docs.github.com/en/free-pro-team@latest/developers/overview/managing-deploy-keys#deploy-keys.
In order to support multi-line deploy keys, spaces in GITHUB_DEPLOY_KEYS are converted
into line shifts. Multiple keys can be separated with a comma (,).