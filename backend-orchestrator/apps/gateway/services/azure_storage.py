import os
import uuid
import logging
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)

class AzureBlobService:
    def __init__(self):
        # Try getting full connection string, or construct it from name and key
        self.connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not self.connection_string:
            account_name = os.environ.get("AZURE_ACCOUNT_NAME")
            account_key = os.environ.get("AZURE_ACCOUNT_KEY")
            if account_name and account_key:
                self.connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
                
        self.container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME") or os.environ.get("AZURE_CONTAINER")

    def upload_image(self, image_file, prefix="uploads"):
        """
        Uploads an image file object to Azure Blob Storage.
        Returns the public URL of the uploaded blob.
        """
        if not self.connection_string or not self.container_name:
            logger.error("[AZURE STORAGE] Missing AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_NAME in environment.")
            return None

        try:
            blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            
            # Create a unique filename
            # Fallback to .jpg if no extension found
            name, ext = os.path.splitext(image_file.name)
            if not ext:
                ext = ".jpg"
                
            blob_name = f"{prefix}/{uuid.uuid4()}{ext}"
            
            blob_client = blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
            
            # Set content type if available
            content_settings = ContentSettings(content_type=image_file.content_type) if hasattr(image_file, "content_type") else None
            
            # Reset the file pointer to the beginning if it was read previously
            image_file.seek(0)
            
            # Upload the file
            blob_client.upload_blob(
                image_file.read(), 
                overwrite=True, 
                content_settings=content_settings
            )
            
            # Reset again for any subsequent services (like vision API) that might need to read it
            image_file.seek(0)
            
            public_url = blob_client.url
            logger.info(f"[AZURE STORAGE] Successfully uploaded image to {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"[AZURE STORAGE] Failed to upload image to Azure: {e}")
            return None

azure_storage_service = AzureBlobService()
