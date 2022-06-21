import logging
import mimetypes
import os
import secrets
import urllib.request

import boto3
import graphene
import requests
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from saleor.core.utils.validators import get_oembed_data
from saleor.graphql.channel import ChannelContext
from saleor.graphql.core.mutations import BaseMutation
from saleor.graphql.core.types.common import Error
from saleor.graphql.product.types import Product
from saleor.product import ProductMediaTypes
from saleor.product.thumbnails import create_product_thumbnails

from uploading.graphql.enums import (
    PreSignedErrorCodeType,
    ProductExtendClassErrorCode,
    ProductExtendError,
)

logger = logging.getLogger(__name__)


def is_image_mimetype(mimetype: str):
    """Check if mimetype is image."""
    return mimetype.startswith("image/")


def is_image_url(url: str):
    """Check if file URL seems to be an image."""
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}
    )
    r = urllib.request.urlopen(req)
    if "image" in r.getheader("Content-Type"):
        return True
    filetype = mimetypes.guess_type(url)[0]
    return filetype is not None and is_image_mimetype(filetype)


def get_filename_from_url(url: str):
    """Prepare unique filename for file from URL to avoid overwritting."""
    file_name = os.path.basename(url)
    name, format = os.path.splitext(file_name)
    hash = secrets.token_hex(nbytes=4)
    return f"{name}_{hash}{format}"


class PreSignedError(Error):
    code = PreSignedErrorCodeType(description="The error code.", required=True)


class CreatePreSignedUrl(BaseMutation):
    policy = graphene.String(description="The policy.")
    url = graphene.String(description="The pre-signed URL.")
    signature = graphene.String(description="The signature.")
    key = graphene.String(description="The key of the object.")
    aws_access_key_id = graphene.String(description="The AWS access key id.")

    class Arguments:
        object_name = graphene.String(
            required=True, description="The object name of the s3 object."
        )
        expires = graphene.Int(
            required=False, description="The expiration time in seconds."
        )

    class Meta:
        error_type_class = PreSignedError
        error_type_field = "account_errors"
        description = "Generate a pre-signed URL to share an S3 object"

    @staticmethod
    def get_s3_pre_signed_url(object_name, expires=3600):
        """Generate a pre-signed URL to share an S3 object."""
        bucket_name = settings.AWS_MEDIA_BUCKET_NAME
        if not bucket_name:
            raise ValidationError(
                "The AWS_MEDIA_BUCKET_NAME environment variable is not set."
            )
        s3_client = boto3.client(
            service_name="s3",
            region_name=settings.AWS_S3_REGION_NAME,
            config=Config(
                signature_version="s3v4",
            ),
        )
        try:
            response = s3_client.generate_presigned_url(
                ExpiresIn=expires,
                ClientMethod="put_object",
                Params={"Bucket": bucket_name, "Key": object_name},
            )
        except ClientError as e:
            logger.error(e)
            raise ValidationError(str(e))
        return response

    @classmethod
    def perform_mutation(cls, root, info, **data):
        expires = data.get("expires", 3600)
        object_name = data.get("object_name")
        try:
            url = cls.get_s3_pre_signed_url(object_name, expires)
        except ValidationError as e:
            return cls.handle_errors(e)
        return CreatePreSignedUrl(
            url=url,
        )


class ProductMediaCreateInputExtended(graphene.InputObjectType):
    alt = graphene.String(description="Alt text for a product media.")
    product_extend = graphene.ID(
        required=True, description="ID of an product.", name="product_extend"
    )
    media_url = graphene.String(
        required=False, description="Represents an URL to an external media."
    )


class ProductMediaCreateExtended(BaseMutation):
    # product_extend = graphene.Field(ProductExtended)
    ok = graphene.Boolean()

    class Arguments:
        input = ProductMediaCreateInputExtended(
            required=True, description="Fields required to create a product media."
        )

    class Meta:
        description = (
            "Create a media object (image or video URL) associated with product. "
            "For image,"
        )
        # permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductExtendError
        error_type_field = "product_errors"

    @classmethod
    def validate_input(cls, data):
        media_url = data.get("media_url")

        if not media_url:
            raise ValidationError(
                {
                    "input": ValidationError(
                        "Image or external URL is required.",
                        code=ProductExtendClassErrorCode.REQUIRED,
                    )
                }
            )

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        data = data.get("input")
        cls.validate_input(data)
        product = cls.get_node_or_error(
            info,
            data["product_extend"],
            only_type=Product,
        )
        print(product)
        alt = data.get("alt", "")
        media_url = data.get("media_url")

        if media_url:
            # Remote URLs can point to the images or oembed data.
            if is_image_url(media_url):
                filename = get_filename_from_url(media_url)
                image_data = requests.get(media_url, stream=True)
                image_file = File(image_data.raw, filename)
                media = product.media.create(
                    image=image_file,
                    alt=alt,
                    type=ProductMediaTypes.IMAGE,
                )
                create_product_thumbnails.delay(media.pk)
            else:
                oembed_data, media_type = get_oembed_data(media_url, "media_url")
                media = product.media.create(
                    external_url=oembed_data["url"],
                    alt=oembed_data.get("title", alt),
                    type=media_type,
                    oembed_data=oembed_data,
                )

        product = ChannelContext(node=product, channel_slug=None)
        if product:
            return ProductMediaCreateExtended(ok=True)
        else:
            return ProductMediaCreateExtended(ok=False)
