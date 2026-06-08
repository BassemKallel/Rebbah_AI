import json
import logging
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.gateway.services.azure_storage import azure_storage_service
from apps.crm.models.analytics import ItemVector

logger = logging.getLogger(__name__)


class CatalogUploadView(APIView):
    """
    Endpoint pour le Dashboard Frontend.
    Reçoit une image locale, l'upload sur Azure, puis l'envoie au Vision Service pour vectorisation.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        shop_id = request.data.get("shop_id")
        item_id = request.data.get("item_id")
        metadata_str = request.data.get("metadata", "{}")
        image_file = request.FILES.get("image")

        if not all([shop_id, item_id, image_file]):
            return Response({"error": "shop_id, item_id, et image sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}

        custom_attributes_raw = request.data.get('custom_attributes')
        if custom_attributes_raw:
            try:
                custom_dict = json.loads(custom_attributes_raw)
                metadata.update(custom_dict)
            except json.JSONDecodeError:
                pass

        # 1. Upload l'image sur Azure (Le fichier physique devient une URL publique)
        image_url = azure_storage_service.upload_image(image_file, prefix=shop_id)
        if not image_url:
            return Response({"error": "Echec de l'upload sur Azure Storage."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Construction du texte à embedder (Nom + Description)
        text_to_embed = None
        if metadata:
            name = metadata.get("name", "")
            desc = metadata.get("description", "")
            if name or desc:
                text_to_embed = f"{name} - {desc}".strip()

        # 3. Envoie l'URL publique, le texte et les infos au service Vision pour l'IA (Fusion Multimodale)
        try:
            vision_url = settings.VISION_SERVICE_URL.rstrip('/') + '/vectorize'
            res = requests.post(
                vision_url,
                json={
                    "image_url": image_url,
                    "text_to_embed": text_to_embed,
                    "item_id": item_id,
                    "shop_id": shop_id,
                    "metadata": metadata
                },
                timeout=15
            )
            if res.status_code == 200:
                return Response({
                    "status": "success",
                    "message": "Produit uploadé sur Azure et vectorisé avec succès !",
                    "azure_url": image_url,
                    "vision_response": res.json()
                })
            else:
                return Response({"error": f"Erreur Vision Service: {res.text}"}, status=res.status_code)
        except Exception as e:
            return Response({"error": f"Erreur de communication avec Vision Service: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CatalogUpdateMetadataView(APIView):
    """
    Met à jour uniquement les métadonnées d'un produit existant
    (nom, prix, description, in_stock) sans re-vectoriser l'image.
    """
    permission_classes = [AllowAny]

    def patch(self, request):
        shop_id     = request.data.get("shop_id")
        item_id     = request.data.get("item_id")
        metadata_in = request.data.get("metadata", {})

        if not all([shop_id, item_id]):
            return Response({"error": "shop_id et item_id sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse metadata if it came as a JSON string
        if isinstance(metadata_in, str):
            try:
                metadata_in = json.loads(metadata_in)
            except json.JSONDecodeError:
                metadata_in = {}

        try:
            item = ItemVector.objects.get(item_id=item_id, shop_id=shop_id)
        except ItemVector.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Merge incoming metadata into existing
        existing_meta = item.metadata or {}
        new_meta = {}
        for k, v in metadata_in.items():
            new_meta[k] = v
            
        new_meta["name"] = metadata_in.get("name", existing_meta.get("name", ""))
        new_meta["price"] = metadata_in.get("price", existing_meta.get("price", ""))
        new_meta["description"] = metadata_in.get("description", existing_meta.get("description", ""))
        new_meta["in_stock"] = metadata_in.get("in_stock", existing_meta.get("in_stock", True))

        item.metadata = new_meta
        item.save(update_fields=["metadata"])

        logger.info(f"[CATALOG] Metadata updated for item_id={item_id} shop_id={shop_id}")
        return Response({"status": "success", "message": "Métadonnées mises à jour.", "metadata": new_meta})


class CatalogImportCsvView(APIView):
    """
    Importe un catalogue via un fichier CSV.
    Les produits sont créés sans image ni vecteur (Vector RAG).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import csv
        import uuid
        import io

        shop_id = request.data.get("shop_id")
        csv_file = request.FILES.get("file")

        if not shop_id or not csv_file:
            return Response({"error": "shop_id et file (CSV) sont requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string, delimiter=',')
            
            if reader.fieldnames and ';' in reader.fieldnames[0]:
                io_string.seek(0)
                reader = csv.DictReader(io_string, delimiter=';')

            items_created = 0
            for row in reader:
                row_lower = {k.lower().strip() if k else '': v for k, v in row.items()}
                
                name = row_lower.get("name", "").strip()
                if not name:
                    name = row_lower.get("nom", "").strip()
                if not name:
                    continue
                
                price = row_lower.get("price", "").strip()
                if not price:
                    price = row_lower.get("prix", "").strip()
                    
                description = row_lower.get("description", "").strip()
                
                in_stock_str = str(row_lower.get("in_stock", "true")).strip().lower()
                in_stock = in_stock_str in ["true", "1", "yes", "oui", "vrai", "v"]

                metadata = {
                    "name": name,
                    "price": price,
                    "description": description,
                    "in_stock": in_stock
                }
                
                standard_keys = ['name', 'nom', 'price', 'prix', 'description', 'in_stock', 'stock']
                for k, v in row.items():
                    if k and k.lower().strip() not in standard_keys:
                        val = v.strip() if isinstance(v, str) else v
                        if val:
                            metadata[k.strip()] = val
                
                item_id = f"prod_{uuid.uuid4().hex[:8]}"

                ItemVector.objects.create(
                    item_id=item_id,
                    shop_id=shop_id,
                    metadata=metadata,
                    image_url="",
                    embedding=None
                )
                items_created += 1

            return Response({
                "status": "success", 
                "message": f"{items_created} produits importés avec succès !",
                "count": items_created
            })
            
        except Exception as e:
            logger.error(f"[CSV IMPORT] Error: {e}")
            return Response({"error": f"Erreur lors de l'import CSV : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
