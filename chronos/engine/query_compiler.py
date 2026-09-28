"""
CHRONOS Neuro-Symbolic Query Compiler.

Parses compound natural language queries into the Typed Query Algebra (Stage 9):
    Q ::= Sem(text) | Chg(type) | Spa(relation, target, dist) | Meta(...)

Example:
    "newly built structures near a river"
    -> Sem("built structures") ^ Chg("construction") ^ Spa("ST_DWithin", "waterway", 500)
"""

import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class QueryPlan:
    semantic_target: Optional[str] = None
    change_type: Optional[str] = None
    spatial_relation: Optional[str] = None
    spatial_target: Optional[str] = None
    spatial_distance_m: float = 500.0


def parse_query_rule_based(query: str) -> QueryPlan:
    """
    Deterministic rule-based fallback parser for air-gapped demo
    when the local LLM is unavailable.
    """
    query = query.lower()
    plan = QueryPlan()
    
    # 1. Spatial relations
    if "near " in query:
        plan.spatial_relation = "ST_DWithin"
        parts = query.split("near ")
        plan.semantic_target = parts[0].strip()
        target = parts[1].strip()
        if "river" in target or "water" in target:
            plan.spatial_target = "waterway=*"
        elif "road" in target or "highway" in target:
            plan.spatial_target = "highway=*"
        else:
            plan.spatial_target = target
            
    # 2. Change modifiers
    if "newly built" in query or "construction" in query:
        plan.change_type = "construction"
        if plan.semantic_target:
            plan.semantic_target = plan.semantic_target.replace("newly built", "").strip()
    elif "cleared" in query or "deforestation" in query:
        plan.change_type = "clearance"
        
    # If no spatial relation, the whole query is the semantic target
    if not plan.semantic_target and not plan.spatial_relation:
        plan.semantic_target = query
        
    return plan

def compile_to_sql(plan: QueryPlan) -> str:
    """
    Compiles the parsed query plan into a PostGIS SQL WHERE clause
    for push-down filtering before vector search.
    """
    clauses = []
    if plan.spatial_relation == "ST_DWithin" and plan.spatial_target:
        clauses.append(
            f"ST_DWithin(geom, (SELECT geom FROM osm_features WHERE type = '{plan.spatial_target}' LIMIT 1), {plan.spatial_distance_m})"
        )
    
    if not clauses:
        return "1=1"
        
    return " AND ".join(clauses)
