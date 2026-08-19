from app.services.shared_relations.contract import (
    PossibleDuplicate,
    SharedRelation,
    SharedRelationDetail,
    SharedRelationListResponse,
    make_relation_id,
    parse_relation_id,
)
from app.services.shared_relations.service import (
    get_shared_relation,
    get_shared_relation_detail,
    list_duplicate_candidates,
    list_shared_relations,
)

__all__ = [
    "PossibleDuplicate",
    "SharedRelation",
    "SharedRelationDetail",
    "SharedRelationListResponse",
    "make_relation_id",
    "parse_relation_id",
    "get_shared_relation",
    "get_shared_relation_detail",
    "list_duplicate_candidates",
    "list_shared_relations",
]
