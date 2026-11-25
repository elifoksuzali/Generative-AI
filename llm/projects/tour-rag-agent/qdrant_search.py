import json
import os
from typing import Dict, List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http import models
from openai import OpenAI
from pydantic import BaseModel

# Qdrant veritabanı bağlantı ayarları
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "turlar"

# OpenAI API ayarları (soru analizi için)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")  # Kendi API anahtarınızı ekleyin veya environment variable olarak ayarlayın
openai_client = OpenAI(api_key=OPENAI_API_KEY)


class SoruAnalizi(BaseModel):
    """Sorudan çıkarılan alanlar"""
    gecesayisi: Optional[int] = None
    konaklama: Optional[str] = None
    turtipi: Optional[str] = None
    diğer_alanlar: Dict[str, Any] = {}


class AgentSistem:
    def __init__(self):
        self.qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.filtreleme_search_list = ["gecesayisi", "turtipi"]
        
    def soru_analiz_agent(self, soru: str) -> SoruAnalizi:
        """
        1. Adım: Soruyu analiz edip konaklama, gecesayisi gibi alanları çıkarır
        """
        prompt = f"""
        Aşağıdaki kullanıcı sorusunu analiz et ve belirtilen alanları çıkar.
        Soru: {soru}
        
        Çıkarılacak alanlar:
        - gecesayisi: Gece sayısı (sadece sayı olarak, varsa)
        - konaklama: Otel veya konaklama bilgisi (örn: "5* otel", "4* otel konaklamalı")
        - turtipi: Tur tipi (yurt içi veya yurt dışı, varsa)
        
        Sonucu JSON formatında döndür. Örnek:
        {{"gecesayisi": 2, "konaklama": "5* otel", "turtipi": null}}
        """
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sen bir tur sorgu analiz uzmanısın. Sorulardan yapılandırılmış bilgi çıkarıyorsun."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            result_text = response.choices[0].message.content.strip()
            # JSON'u temizle (eğer markdown code block içindeyse)
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result_dict = json.loads(result_text)
            return SoruAnalizi(**result_dict)
            
        except Exception as e:
            print(f"Soru analiz hatası: {e}")
            # Fallback: Basit regex ile gece sayısını bul
            import re
            gece_match = re.search(r'(\d+)\s*gece', soru, re.IGNORECASE)
            gecesayisi = int(gece_match.group(1)) if gece_match else None
            
            konaklama_match = re.search(r'(\d+\*\s*otel[^.]*)', soru, re.IGNORECASE)
            konaklama = konaklama_match.group(1).strip() if konaklama_match else None
            
            return SoruAnalizi(gecesayisi=gecesayisi, konaklama=konaklama)
    
    def arama_yontemi_belirle(self, analiz: SoruAnalizi) -> Dict[str, Any]:
        """
        2. Adım: Hangi alanların filter search, hangilerinin multivector search için kullanılacağını belirler
        """
        filter_search_değerleri = {}
        multivector_search_değerleri = {}
        
        # Filtreleme search listesindeki alanları kontrol et
        if analiz.gecesayisi is not None and "gecesayisi" in self.filtreleme_search_list:
            filter_search_değerleri["gecesayisi"] = analiz.gecesayisi
        
        if analiz.turtipi is not None and "turtipi" in self.filtreleme_search_list:
            filter_search_değerleri["turtipi"] = analiz.turtipi
        
        # Diğer alanlar multivector search için
        if analiz.konaklama is not None:
            multivector_search_değerleri["konaklama"] = analiz.konaklama
        
        return {
            "filter_search": filter_search_değerleri,
            "multivector_search": multivector_search_değerleri
        }
    
    def qdrant_hybrid_search(self, arama_yontemleri: Dict[str, Any], limit: int = 4) -> List[Dict]:
        """
        3-6. Adımlar: Qdrant'ta hybrid search (filter + multivector) yapar
        Tek bir istekte hem filter hem de search yapılır
        """
        # Filter oluştur
        conditions = []
        
        if "gecesayisi" in arama_yontemleri["filter_search"]:
            conditions.append(
                FieldCondition(
                    key="gecesayisi",
                    match=MatchValue(value=arama_yontemleri["filter_search"]["gecesayisi"])
                )
            )
        
        if "turtipi" in arama_yontemleri["filter_search"]:
            conditions.append(
                FieldCondition(
                    key="turtipi",
                    match=MatchValue(value=arama_yontemleri["filter_search"]["turtipi"])
                )
            )
        
        query_filter = Filter(must=conditions) if conditions else None
        
        # Multivector search için query metni
        query_text = ""
        if arama_yontemleri["multivector_search"]:
            query_text = " ".join(arama_yontemleri["multivector_search"].values())
        
        # Qdrant'ta hybrid search (filter + vector search)
        # Önce semantic search yapıp sonra filter uygulanır
        if query_text:
            # Multivector search için embedding oluştur
            try:
                embedding_response = openai_client.embeddings.create(
                    input=query_text,
                    model="text-embedding-ada-002"
                )
                query_vector = embedding_response.data[0].embedding
            except Exception as e:
                print(f"Embedding oluşturma hatası: {e}")
                # Fallback: basit embedding (gerçek uygulamada mutlaka embedding kullanılmalı)
                query_vector = [0.0] * 1536  # text-embedding-ada-002 boyutu
            
            # Qdrant hybrid search: filter + vector search birlikte
            search_results = self.qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=0.5
            )
        else:
            # Sadece filter search
            if query_filter:
                # Filter ile scroll yap
                results = self.qdrant_client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=query_filter,
                    limit=limit
                )
                search_results = [
                    models.ScoredPoint(
                        id=point.id,
                        score=1.0,
                        payload=point.payload
                    )
                    for point in results[0]
                ]
            else:
                search_results = []
        
        # Sonuçları formatla
        sonuclar = []
        for result in search_results:
            sonuclar.append({
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            })
        
        return sonuclar
    
    def tur_arama(self, soru: str, limit: int = 4) -> List[Dict]:
        """
        Ana fonksiyon: Soruyu alır, analiz eder ve Qdrant'ta arama yapar
        """
        # 1. Soru analizi
        analiz = self.soru_analiz_agent(soru)
        print(f"Analiz sonucu: {analiz.dict()}")
        
        # 2. Arama yöntemi belirleme
        arama_yontemleri = self.arama_yontemi_belirle(analiz)
        print(f"Arama yöntemleri: {arama_yontemleri}")
        
        # 3-6. Qdrant hybrid search
        sonuclar = self.qdrant_hybrid_search(arama_yontemleri, limit)
        
        return sonuclar


def qdrant_veri_yukle():
    """
    Qdrant'a örnek verileri yükler
    """
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Collection oluştur (eğer yoksa)
    try:
        client.get_collection(COLLECTION_NAME)
    except:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)  # text-embedding-ada-002 boyutu
        )
    
    # Örnek veriler
    turlar = [
        {"id": 1, "adı": "istanbul turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 2, "adı": "malatya turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 3, "adı": "trabzon turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel konaklamalı"},
        {"id": 4, "adı": "bologna turu", "gecesayisi": 3, "turtipi": "yurt dışı", "konaklama": "5* otel"},
        {"id": 5, "adı": "nursum turu", "gecesayisi": 2, "turtipi": "yurt dışı", "konaklama": "5* otel"},
        {"id": 6, "adı": "efdal turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel"},
        {"id": 7, "adı": "tai turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel konaklamalı"},
        {"id": 8, "adı": "bologna turu", "gecesayisi": 3, "turtipi": "yurt dışı", "konaklama": "5* otel"},
        {"id": 9, "adı": "tır turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 10, "adı": "edirne turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 11, "adı": "eskişehir turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel konaklamalı"},
        {"id": 12, "adı": "bursa turu", "gecesayisi": 3, "turtipi": "yurt dışı", "konaklama": "5* otel"},
        {"id": 13, "adı": "çanakkale turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 14, "adı": "rize turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 15, "adı": "giresun turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel konaklamalı"},
        {"id": 16, "adı": "timrim turu", "gecesayisi": 3, "turtipi": "yurt dışı", "konaklama": "5* otel"},
        {"id": 17, "adı": "muzmuz turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 18, "adı": "kahgag turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 19, "adı": "gılıgılı turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel konaklamalı"},
        {"id": 20, "adı": "cızbız turu", "gecesayisi": 3, "turtipi": "yurt dışı", "konaklama": "5* otel"},
        {"id": 21, "adı": "sims turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 22, "adı": "arhavi turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "5* otel"},
        {"id": 23, "adı": "gaybana turu", "gecesayisi": 2, "turtipi": "yurt içi", "konaklama": "4* otel konaklamalı"},
        {"id": 24, "adı": "semş turu", "gecesayisi": 3, "turtipi": "yurt dışı", "konaklama": "5* otel"},
    ]
    
    # Embedding oluştur ve yükle
    points = []
    for tur in turlar:
        # Her tur için embedding oluştur (adı + konaklama bilgisi)
        text_for_embedding = f"{tur['adı']} {tur['konaklama']}"
        
        try:
            embedding_response = openai_client.embeddings.create(
                input=text_for_embedding,
                model="text-embedding-ada-002"
            )
            vector = embedding_response.data[0].embedding
        except Exception as e:
            print(f"Embedding oluşturma hatası: {e}")
            # Fallback: basit vektör
            import random
            vector = [random.random() for _ in range(1536)]  # text-embedding-ada-002 boyutu
        
        points.append(
            PointStruct(
                id=tur["id"],
                vector=vector,
                payload={
                    "adı": tur["adı"],
                    "gecesayisi": tur["gecesayisi"],
                    "turtipi": tur["turtipi"],
                    "konaklama": tur["konaklama"]
                }
            )
        )
    
    # Qdrant'a yükle
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"{len(turlar)} tur Qdrant'a yüklendi!")


if __name__ == "__main__":
    # Örnek kullanım
    agent = AgentSistem()
    
    # İlk çalıştırmada verileri yükle (sadece bir kez)
    # qdrant_veri_yukle()
    
    # Soru sor
    soru = "2 gece 5* otel turların var mı"
    sonuclar = agent.tur_arama(soru, limit=4)
    
    print("\n" + "="*50)
    print(f"Soru: {soru}")
    print("="*50)
    print(f"\nBulunan {len(sonuclar)} tur:\n")
    
    for sonuc in sonuclar:
        payload = sonuc["payload"]
        print(f"ID: {sonuc['id']}")
        print(f"Adı: {payload['adı']}")
        print(f"Gece Sayısı: {payload['gecesayisi']}")
        print(f"Tur Tipi: {payload['turtipi']}")
        print(f"Konaklama: {payload['konaklama']}")
        print(f"Score: {sonuc['score']:.4f}")
        print("-" * 30)

