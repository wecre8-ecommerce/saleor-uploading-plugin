from enum import Enum

import graphene
from saleor.graphql.core.types.common import Error


class PreSignedErrorCode(Enum):
    INVALID = "invalid"


PreSignedErrorCodeType = graphene.Enum.from_enum(PreSignedErrorCode)


class ProductExtendClassErrorCode(Enum):

    INVALID_FIELD_VALUE = "invalid_field_value"

    REQUIRED = "required"


ProductExtendErrorCode = graphene.Enum.from_enum(ProductExtendClassErrorCode)


class ProductExtendError(Error):
    code = ProductExtendErrorCode(description="The error code.", required=True)
