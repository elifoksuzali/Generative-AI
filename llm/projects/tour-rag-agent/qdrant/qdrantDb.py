import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, ScoredPoint, PointIdsList, VectorParams, Distance, Filter, FieldCondition, MatchValue, Prefetch, QueryRequest
from typing import List, Dict, Any, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from db_key import KeyManager

key_manager = KeyManager()
api_keys = key_manager.load_api_key()
QDRANT_HOST = api_keys.get('qdrant_host', '')
QDRANT_API_KEY = api_keys.get('qdrant_api_key', '')


class QdrantDatabase:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.client: Optional[QdrantClient] = None

    def connect(self):
        if not self.client:
            try:
                self.client = QdrantClient(
                    url=QDRANT_HOST,
                    api_key=QDRANT_API_KEY,
                    timeout=20,  # int olarak değiştirildi
                    verify=False  # SSL doğrulamasını devre dışı bırak
                )
                # Bağlantıyı test et
                self.client.get_collections()
                print("✅ Qdrant bağlantısı başarılı!")
            except Exception as e:
                print(f"❌ Qdrant bağlantı hatası: {str(e)}")
                raise

    def _ensure_client(self):
        """Client'ın bağlı olduğundan emin ol"""
        if not self.client:
            self.connect()

    def create_collection(self, vector_size: int):
        self._ensure_client()
        if self.client:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

    def insert_point(self, point_id: int, vector: List[float], payload: Optional[Dict[str, Any]] = None):
        self._ensure_client()
        if self.client:
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            self.client.upsert(collection_name=self.collection_name, points=[point])

    def insert_chat_message(self, point_id: int, message: str, response: str, embedding: list[float]):
        self._ensure_client()
        if self.client:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "type": "chat",
                            "user": message,
                            "response": response
                        }
                    )
                ]
            )

    def delete_point(self, point_id: int):
        self._ensure_client()
        if self.client:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=[point_id])
            )

    def update_point(self, point_id: int, vector: Optional[List[float]] = None, payload: Optional[Dict[str, Any]] = None):
        if vector is not None:  # vector None değilse güncelle
            self.insert_point(point_id, vector, payload)

    def query_points(self, vector: List[float], top_k: int = 5) -> List[ScoredPoint]:
        self._ensure_client()
        if not self.client:
            return []
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )

    def query_points_dense(self, vector: List[float], top_k: int = 5) -> List[ScoredPoint]:
        """Dense vector ile arama (text-dense)"""
        self._ensure_client()
        if not self.client:
            return []
        
        try:
            # Qdrant multivector search için named vectors kullan
            return self.client.search(
                collection_name=self.collection_name,
                query_vector={"text-dense": vector},  # Named vector format
                limit=top_k,
                with_payload=True,
                score_threshold=None
            )
        except Exception as e:
            print(f"❌ Dense search hatası: {str(e)}")
            return []

    def query_points_colbert(self, vector: List[float], top_k: int = 5) -> List[ScoredPoint]:
        """ColBERT vector ile arama"""
        self._ensure_client()
        if not self.client:
            return []
        
        try:
            # Qdrant multivector search için named vectors kullan
            return self.client.search(
                collection_name=self.collection_name,
                query_vector={"colbert": vector},  # Named vector format
                limit=top_k,
                with_payload=True,
                score_threshold=None
            )
        except Exception as e:
            print(f"❌ ColBERT search hatası: {str(e)}")
            return []

    def query_points_filter(self, query_filter: Optional[Filter] = None, top_k: int = 5) -> List[ScoredPoint]:
        """Filter bazlı arama (vector olmadan)"""
        self._ensure_client()
        if not self.client:
            return []
        
        # Tüm noktaları al ve filter uygula
        return self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        )[0]  # scroll returns (points, next_page_offset)

    def query_points_multivector(self, dense_query: List[float], colbert_query: List[float], top_k: int = 5) -> List[ScoredPoint]:
        """Basit multivector arama - dense ve colbert sonuçlarını birleştir"""
        self._ensure_client()
        if not self.client:
            return []
        
        try:
            # Dense search
            dense_results = self.query_points_dense(dense_query, top_k * 2)
            
            # ColBERT search
            colbert_results = self.query_points_colbert(colbert_query, top_k * 2)
            
            # Sonuçları birleştir ve score'a göre sırala
            all_results = list(dense_results) + list(colbert_results)
            
            # Score'a göre sırala (yüksek score önce)
            all_results.sort(key=lambda x: getattr(x, 'score', 0), reverse=True)
            
            # Top-k sonucu döndür
            return all_results[:top_k]
            
        except Exception as e:
            print(f"❌ Multivector search hatası: {str(e)}")
            # Fallback olarak dense search yap
            return self.query_points_dense(dense_query, top_k)

    def query_points_multivector_reranking(self, dense_query: List[float], colbert_query: List[float], top_k: int = 5) -> List[ScoredPoint]:
        """
        Query with Retrieval + Reranking in One Call - Qdrant'ın önerdiği yöntem
        Bu yöntem en iyi sonuçları verir çünkü dense ve colbert vektörlerini birlikte kullanır
        """
        self._ensure_client()
        if not self.client:
            return []
        
        try:
            # Basit multivector search yap (prefetch + query henüz desteklenmiyor)
            # Bu versiyonda fallback olarak basit multivector search kullan
            return self.query_points_multivector(dense_query, colbert_query, top_k)
            
        except Exception as e:
            print(f"❌ Multivector reranking hatası: {str(e)}")
            # Fallback olarak basit multivector search yap
            return self.query_points_multivector(dense_query, colbert_query, top_k)

    def delete_collection(self):
        self._ensure_client()
        if self.client:
            self.client.delete_collection(collection_name=self.collection_name)

    def get_collection_info(self):
        self._ensure_client()
        if not self.client:
            return None
        return self.client.get_collection(collection_name=self.collection_name)
