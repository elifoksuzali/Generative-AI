import sys
import os
import argparse
import json
import requests
from typing import Dict, List, Any

def multivector_search(fields_str, limit=50):
    """
    Multivector search - birden fazla vector field ile arama
    """
    try:
        qdrant_url = "http://127.0.0.1:6333/collections/mng_01_09_25/points/search"
        
        # Fields'ları parse et
        fields = []
        if fields_str:
            field_pairs = fields_str.split(";")
            for pair in field_pairs:
                if ":" in pair:
                    field, value = pair.split(":", 1)
                    fields.append({"field": field.strip(), "value": value.strip()})
        
        # Query text oluştur
        query_text = " ".join([f["value"] for f in fields]) if fields else "tur"
        
        request_body = {
            "searches": [
                {
                    "vector": {
                        "name": "konaklama_sparse",
                        "vector": [0.1] * 1000
                    },
                    "text": query_text,
                    "limit": limit // 2,
                    "with_payload": True,
                    "with_vector": False
                },
                {
                    "vector": {
                        "name": "text-dense",
                        "vector": [0.1] * 1000
                    },
                    "text": query_text,
                    "limit": limit // 2,
                    "with_payload": True,
                    "with_vector": False
                }
            ]
        }
        
        print(f"🔍 Multivector Search - Query: {query_text}")
        print(f"   Alanlar: {[f'{f["field"]}:{f["value"]}' for f in fields]}")
        
        response = requests.post(qdrant_url, json=request_body)
        
        if response.status_code == 200:
            result = response.json()
            all_points = []
            for search_result in result.get("result", []):
                all_points.extend(search_result.get("result", []))
            
            return {
                "success": True,
                "method": "multivector",
                "data": all_points,
                "count": len(all_points)
            }
        else:
            return {
                "success": False,
                "method": "multivector",
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "method": "multivector",
            "error": str(e)
        }

