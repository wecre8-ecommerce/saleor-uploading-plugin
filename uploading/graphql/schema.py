import graphene
from graphene_federation import build_schema
from uploading.graphql.mutations import (CreatePreSignedUrl,
                                         ProductMediaCreateExtended)


class Query(graphene.ObjectType):
    create_pre_signed_url = CreatePreSignedUrl.Field()


class Mutation(graphene.ObjectType):
    create_pre_signed_url = CreatePreSignedUrl.Field()
    product_media_create_extended = ProductMediaCreateExtended.Field()


schema = build_schema(query=Query, mutation=Mutation)
