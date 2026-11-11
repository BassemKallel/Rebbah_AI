import React, { useState } from 'react';
import { RefreshCcw, Plus, LayoutGrid, List, FileUp } from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';
import Toast from '../../components/ui/Toast';
import { useCatalog } from '../../hooks/useCatalog';
import { ProductCard } from '../../components/catalog/ProductCard';
import { ProductEmptyState } from '../../components/catalog/ProductEmptyState';
import { DeleteConfirmModal } from '../../components/catalog/DeleteConfirmModal';
import { ProductFormModal } from '../../components/catalog/ProductFormModal';

const ProductSync = () => {
  const { shopId } = useAuth();
  const { items, loading, loadCatalog, removeProduct, saveProduct, importCsv } = useCatalog(shopId);

  // UX States
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [itemToDelete, setItemToDelete] = useState<number | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const handleDelete = async () => {
    if (!itemToDelete) return;
    try {
      await removeProduct(itemToDelete);
      setToast({ message: "Produit supprimé avec succès.", type: "success" });
    } catch (err) {
      setToast({ message: "Erreur lors de la suppression.", type: "error" });
    } finally {
      setItemToDelete(null);
    }
  };

  const handleEdit = (item: any) => {
    setEditingItem(item);
    setIsModalOpen(true);
  };

  const handleCreate = () => {
    setEditingItem(null);
    setIsModalOpen(true);
  };

  const handleSave = async (formData: any) => {
    if (!shopId) return;
    try {
      await saveProduct(shopId, editingItem, formData);
      setToast({ type: 'success', message: 'Produit enregistré avec succès.' });
      setIsModalOpen(false);
    } catch (err) {
      setToast({ type: 'error', message: 'Erreur lors de l\'enregistrement.' });
    }
  };

  const handleCsvImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!shopId || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    
    try {
      const res = await importCsv(shopId, file);
      setToast({ type: 'success', message: res.message || 'Catalogue importé avec succès !' });
    } catch (err) {
      setToast({ type: 'error', message: 'Erreur lors de l\'import du fichier CSV.' });
    }
    
    // Reset file input
    e.target.value = '';
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 mb-1">Catalogue Boutique</h1>
          <p className="text-[13px] font-medium text-gray-500">
            Produits que l'agent IA peut consulter et vendre.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md transition-colors ${viewMode === 'grid' ? 'bg-white shadow-sm text-[#0f6885]' : 'text-gray-500 hover:text-gray-900'}`}
              title="Vue Grille"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition-colors ${viewMode === 'list' ? 'bg-white shadow-sm text-[#0f6885]' : 'text-gray-500 hover:text-gray-900'}`}
              title="Vue Liste"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
          <label className="flex items-center gap-2 bg-white text-[#0f6885] border border-[#0f6885] hover:bg-[#0f6885] hover:text-white font-bold text-sm px-4 py-2 rounded-lg transition-all shadow-sm cursor-pointer">
            <FileUp className="w-4 h-4" /> Importer CSV
            <input type="file" accept=".csv" className="hidden" onChange={handleCsvImport} />
          </label>
          <button onClick={loadCatalog} className="flex items-center gap-2 bg-white text-gray-700 hover:text-[#0f6885] border border-gray-200 hover:border-[#0f6885] font-bold text-sm px-4 py-2 rounded-lg transition-all shadow-sm">
            <RefreshCcw className="w-4 h-4" /> Actualiser
          </button>
          <button onClick={handleCreate} className="flex items-center gap-2 bg-[#0f6885] hover:bg-[#0c5973] text-white font-bold text-sm px-4 py-2 rounded-lg transition-all shadow-sm">
            <Plus className="w-4 h-4" /> Ajouter un Produit
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0f6885]"></div>
          <p className="text-sm font-medium text-gray-500">Chargement du catalogue...</p>
        </div>
      ) : items.length === 0 ? (
        <ProductEmptyState onCreate={handleCreate} />
      ) : (
        <div className={viewMode === 'grid' ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5" : "flex flex-col gap-4"}>
          {items.map(item => (
            <ProductCard 
              key={item.id} 
              item={item} 
              viewMode={viewMode}
              onEdit={handleEdit} 
              onDelete={(id) => setItemToDelete(id)} 
            />
          ))}
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      
      {itemToDelete && (
        <DeleteConfirmModal 
          onClose={() => setItemToDelete(null)} 
          onConfirm={handleDelete} 
        />
      )}

      {isModalOpen && (
        <ProductFormModal 
          editingItem={editingItem} 
          onClose={() => setIsModalOpen(false)} 
          onSave={handleSave} 
        />
      )}
    </div>
  );
};

export default ProductSync;
