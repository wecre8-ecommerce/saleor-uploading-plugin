import graphene
from graphene import relay

from saleor.graphql.core.connection import CountableDjangoObjectType
from saleor.product.product_images import get_thumbnail

from ....product import models


class ProductMediaExtended(CountableDjangoObjectType):
    url = graphene.String(
        required=True,
        description="The URL of the media.",
        size=graphene.Int(description="Size of the image."),
    )

    class Meta:
        description = "Represents a product media."
        fields = ["alt", "id", "sort_order", "type", "oembed_data"]
        interfaces = [relay.Node]
        model = models.ProductMedia

    @staticmethod
    def resolve_url(root: models.ProductMedia, info, *, size=None):
        if root.external_url:
            return root.external_url

        if size:
            url = get_thumbnail(root.image, size, method="thumbnail")
        else:
            url = root.image.url
        return info.context.build_absolute_uri(url)
