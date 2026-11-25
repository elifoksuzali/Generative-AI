import sys
import os
import argparse
import json
import requests
from typing import Dict, List, Any
import re
from config import URL_LINK

# Filter search için kullanılacak ana alanlar
FILTER_SEARCH_FIELDS = {
    "turtipi", "vizesiz", "ulasimtipi", "turkodu", "gecesayisi", "kesinkalkis"
}



def create_filter_only_search(filter_fields):
    """
    Sadece filter search için gerekli koşulları oluşturur
    """
    field_mappings = {
        "gecesayisi": "gecesayisi",
        "turtipi": "turtipi",
        "ulasimtipi": "ulasimtipi",
        "vizesiz": "vizesiz",
        "kesinkalkis": "kesinkalkis",
        "turkodu": "turkodu"
    }
    
    must_conditions = []
    should_conditions = []
    
    for field_info in filter_fields:
        field = field_info["field"]
        value = field_info["value"]
        
        if field in field_mappings:
            # MUST koşulu ekle
            must_condition = {
                "key": field_mappings[field],
                "match": {"value": value}
            }
            must_conditions.append(must_condition)
            
            # SHOULD koşulu da ekle (alternatif arama için)
            should_condition = {
                "key": field_mappings[field],
                "match": {"value": value}
            }
            should_conditions.append(should_condition)
    
    return {
        "must": must_conditions,
        "should": should_conditions
    }

def search_structured(qdrant_params, has_category_match=False):
    """
    Yapısal arama (filter-based) - Önce must, sonra should dener
    """
    try:
        qdrant_url = f"{URL_LINK}/collections/mng/points/scroll"
        
        # 1. Önce must ile dene
        must_filter = {"must": qdrant_params["filter"].get("must", [])}
        request_body = {
            "filter": must_filter,
            "limit": qdrant_params["limit"],
            "with_payload": qdrant_params["with_payload"],
            "with_vector": False
        }
        
        print(f"🔧 DEBUG - Qdrant Filter (MUST):")
        print(json.dumps(request_body, indent=2, ensure_ascii=False))
        
        response = requests.post(qdrant_url, json=request_body)
        
        if response.status_code == 200:
            result = response.json()
            points = result.get("result", {}).get("points", [])
            
            if points:
                print(f"✅ MUST ile {len(points)} sonuç bulundu")
                # Eğer kategori eşleşmesi varsa, puan'a göre sırala
                if has_category_match:
                    points = sorted(points, key=lambda x: 
                        int(x.get("payload", {}).get("turKategori", [{}])[0].get("puan", 0)), 
                        reverse=True
                    )
                    print(f"📊 Kategori puanına göre sıralandı (büyükten küçüğe)")
                
                return {
                    "success": True,
                    "method": "structured_must",
                    "data": points,
                    "count": len(points)
                }
            else:
                print(f"❌ MUST ile sonuç bulunamadı, SHOULD ile deneniyor...")
        else:
            print(f"❌ MUST araması HTTP hatası: {response.status_code}, SHOULD ile deneniyor...")
        
        # 2. Must ile sonuç yoksa should ile dene
        if qdrant_params["filter"].get("should") and len(qdrant_params["filter"]["should"]) > 0:
            should_filter = {
                "should": qdrant_params["filter"]["should"]
            }
            
            request_body = {
                "filter": should_filter,
                "with_payload": qdrant_params["with_payload"],
                "with_vector": False
            }
            
            print(f"🔧 DEBUG - Qdrant Filter (SHOULD):")
            print(json.dumps(request_body, indent=2, ensure_ascii=False))
            
            response = requests.post(qdrant_url, json=request_body)
            
            if response.status_code == 200:
                result = response.json()
                points = result.get("result", {}).get("points", [])
                
                if points:
                    print(f"✅ SHOULD ile {len(points)} sonuç bulundu")
                    # Eğer kategori eşleşmesi varsa, puan'a göre sırala
                    if has_category_match:
                        points = sorted(points, key=lambda x: 
                            int(x.get("payload", {}).get("turKategori", [{}])[0].get("puan", 0)), 
                            reverse=True
                        )
                        print(f"📊 Kategori puanına göre sıralandı (büyükten küçüğe)")
                    
                    return {
                        "success": True,
                        "method": "structured_should",
                        "data": points,
                        "count": len(points)
                    }
                else:
                    print(f"❌ SHOULD ile de sonuç bulunamadı")
            else:
                print(f"❌ SHOULD araması HTTP hatası: {response.status_code}")
        else:
            print(f"❌ SHOULD koşulları bulunamadı")
        
        # 3. Hiçbir sonuç bulunamadı
        print(f"❌ MUST ve SHOULD ile sonuç bulunamadı")
        return {
            "success": True,
            "method": "no_results",
            "data": [],
            "count": 0
        }
            
    except Exception as e:
        return {
            "success": False,
            "method": "structured",
            "error": str(e)
        }
