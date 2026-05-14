import { useState, useCallback, useEffect } from 'react';
import { fetchCatalog, deleteCatalogItem, uploadCatalogItem, updateCatalogMetadata, importCatalogCsv } from '../api/crmApi';

export const useCatalog = (shopId: string | undefined) => {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadCatalog = useCallback(async () => {
    if (!shopId) return;
    setLoading(true);
    try {
      const res = await fetchCatalog(shopId);
      setItems(res.data);
    } catch (err) {
      console.error('Failed to load catalog', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [shopId]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const removeProduct = async (itemId: number) => {
    await deleteCatalogItem(itemId);
    setItems(prev => prev.filter(item => item.id !== itemId));
  };

  const saveProduct = async (shopId: string, editingItem: any, formData: any) => {
    const metadata = {
      name: formData.name,
      price: formData.price,
      description: formData.description,
      in_stock: formData.in_stock,
      ...(formData.customAttributes || {})
    };

    if (editingItem && !formData.selectedFile) {
      await updateCatalogMetadata({
        shop_id: shopId,
        item_id: editingItem.item_id,
        metadata,
      });
    } else {
      const data = new FormData();
      data.append('shop_id', shopId);
      data.append('item_id', editingItem ? editingItem.item_id : `prod_${Date.now()}`);
      data.append('metadata', JSON.stringify(metadata));
      data.append('image', formData.selectedFile!);
      await uploadCatalogItem(data);
    }
    await loadCatalog();
  };

  const importCsv = async (shopId: string, file: File) => {
    const data = new FormData();
    data.append('shop_id', shopId);
    data.append('file', file);
    const res = await importCatalogCsv(data);
    await loadCatalog();
    return res.data;
  };

  return { items, loading, loadCatalog, removeProduct, saveProduct, importCsv };
};
