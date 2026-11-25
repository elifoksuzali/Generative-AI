import os, sys
from qdrant.qdrantDb import QdrantDatabase
import openai
from typing import List, Dict, Any

from openai import OpenAI
from db_key import KeyManager

key_manager = KeyManager()
api_keys = key_manager.load_api_key()
openai_api_key = api_keys.get('gpt_api_key', '')


client = OpenAI(api_key=openai_api_key)

# Qdrant bağlantısı için global değişken
qdrant_client = None

def get_qdrant_client():
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantDatabase("turizm_turlari")
        qdrant_client.connect()
    return qdrant_client

def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def get_context(question: str, q_client: QdrantDatabase = None, num_results: int = 10, offset: int = 0, search_type: str = "default") -> List[Dict[str, Any]]:
    """
    Soru için Qdrant'tan bağlam alır.
    
    Args:
        question: Kullanıcının sorusu
        q_client: Qdrant veritabanı istemcisi (opsiyonel)
        num_results: Alınacak sonuç sayısı
        offset: Başlangıç offset'i (sayfalama için)
        search_type: Arama tipi ("default", "semantic", "multivector", "filter")
    
    Returns:
        List[Dict[str, Any]]: Bulunan sonuçlar
    """
    try:
        # Eğer q_client verilmemişse, global client'ı kullan
        if q_client is None:
            q_client = get_qdrant_client()
        
        print(f"🔍 Qdrant arama tipi: {search_type}")
        
        if search_type == "filter":
            # Filter Search (alan bazlı arama)
            print("   Filter Search yapılıyor...")
            # Basit keyword arama - tüm noktaları al
            results = q_client.query_points(
                query_filter=None,
                top_k=num_results + offset
            )
            
        elif search_type == "semantic":
            # Semantic Search (dense vectors - text-dense)
            print("   Semantic Search yapılıyor...")
            question_vector = get_embedding(question)
            results = q_client.query_points(
                vector=question_vector,
                vector_name="text-dense",  # Yeni vector ismi
                top_k=num_results + offset
            )
            
        elif search_type == "multivector":
            # Multivector Search (dense + sparse)
            print("   Multivector Search yapılıyor...")
            question_vector = get_embedding(question)
            
            # Dense vector search (text-dense)
            dense_results = q_client.query_points(
                vector=question_vector,
                vector_name="text-dense",  # Yeni vector ismi
                top_k=num_results + offset
            )
            
            # Sparse vector search (keyword-based)
            # Basit keyword matching - tüm noktaları al
            sparse_results = q_client.query_points(
                query_filter=None,
                top_k=num_results + offset
            )
            
            # Sonuçları birleştir
            all_results = list(dense_results) + list(sparse_results)
            # Score'a göre sırala
            all_results.sort(key=lambda x: getattr(x, 'score', 0), reverse=True)
            results = all_results[:num_results + offset]
            
        else:
            # Default search (mevcut mantık)
            print("   Default Search yapılıyor...")
            question_vector = get_embedding(question)
            results = q_client.query_points(
                vector=question_vector,
                vector_name="text-dense",  # Yeni vector ismi
                top_k=num_results + offset
            )
        
        # Offset'ten sonraki sonuçları al
        results = results[offset:offset + num_results]
        
        # Sonuçları dönüştür
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "payload": result.payload,
                "text": result.payload.get("dense_text", "")  # Yeni field ismi
            })
        
        print(f"✅ Qdrant'tan {len(formatted_results)} sonuç alındı (tip: {search_type}).")
        return formatted_results
        
    except Exception as e:
        print(f"❌ Qdrant sorgu hatası: {str(e)}")
        return []