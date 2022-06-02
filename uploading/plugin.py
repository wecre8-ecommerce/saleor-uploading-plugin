from saleor.graphql.views import GraphQLView
from saleor.plugins.base_plugin import BasePlugin
from uploading.graphql.schema import schema


class UploadingPlugin(BasePlugin):
    name = "uploading"
    PLUGIN_ID = "uploading"
    PLUGIN_NAME = "uploading"
    DEFAULT_ACTIVE = True
    CONFIGURATION_PER_CHANNEL = False
    PLUGIN_DESCRIPTION = "Plugin for S3 storage links"

    def webhook(self, request, path, previous_value):
        request.app = self
        view = GraphQLView.as_view(schema=schema)
        return view(request)
