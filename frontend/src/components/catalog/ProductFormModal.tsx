import React, { useState, useRef, useEffect } from 'react';
import { X, UploadCloud, Loader2, Plus } from 'lucide-react';

interface ProductFormModalProps {
  editingItem: any | null;
  onClose: () => void;
  onSave: (formData: {
    selectedFile: File | null;
    name: string;
    price: string;
    description: string;
    in_stock: boolean;
  }) => Promise<void>;
}

export const ProductFormModal: React.FC<ProductFormModalProps> = ({ editingItem, onClose, onSave }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  const [formData, setFormData] = useState({ 
    name: '', 
    price: '', 
    description: '', 
    in_stock: true 
  });

  const [customAttributes, setCustomAttributes] = useState<{key: string, value: string}[]>([]);

  useEffect(() => {
    if (editingItem && editingItem.metadata) {
      setFormData({
        name: editingItem.metadata.name || '',
        price: editingItem.metadata.price || '',
        description: editingItem.metadata.description || '',
        in_stock: editingItem.metadata.in_stock !== false,
      });

      // Extract custom attributes (any key that is not standard)
      const standardKeys = ['name', 'price', 'description', 'in_stock'];
      const custom: {key: string, value: string}[] = [];
      Object.entries(editingItem.metadata).forEach(([k, v]) => {
        if (!standardKeys.includes(k) && typeof v === 'string') {
          custom.push({ key: k, value: v });
        }
      });
      setCustomAttributes(custom);
    }
  }, [editingItem]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async () => {
    setIsSaving(true);
    
    // Transform custom attributes array to object
    const customObj = customAttributes.reduce((acc, curr) => {
      if (curr.key.trim() !== '') {
        acc[curr.key.trim()] = curr.value.trim();
      }
      return acc;
    }, {} as Record<string, string>);

    await onSave({
      selectedFile,
      ...formData,
      customAttributes: customObj
    } as any); // Type assertion since we added a new field
    setIsSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">
            {editingItem ? 'Modifier le Produit' : 'Ajouter un Produit'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 flex flex-col gap-5">
          {!editingItem && !previewUrl && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-200 rounded-xl bg-gray-50 p-8 flex flex-col items-center justify-center hover:bg-gray-100 hover:border-[#0f6885]/50 transition-all cursor-pointer group"
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/*"
                onChange={handleFileSelect}
              />
              <UploadCloud className="w-10 h-10 text-gray-400 group-hover:text-[#0f6885] mb-3 transition-colors" />
              <p className="text-sm font-bold text-gray-700 text-center">Cliquez pour uploader une image</p>
              <p className="text-xs text-gray-500 mt-1 text-center">JPG, PNG (max 5MB)</p>
            </div>
          )}

          {!editingItem && previewUrl && (
            <div className="h-40 bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center relative border border-gray-200">
              <img src={previewUrl} alt="Preview" className="h-full object-contain" />
              <button
                onClick={() => { setSelectedFile(null); setPreviewUrl(null); }}
                className="absolute top-2 right-2 bg-white/90 p-1.5 rounded-full shadow-sm text-gray-500 hover:text-red-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {editingItem && editingItem.image_url && (
            <div className="h-40 bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center border border-gray-200">
              <img src={editingItem.image_url} alt="Preview" className="h-full object-contain" />
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-gray-700">Nom du produit</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="bg-white border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-medium focus:outline-none focus:ring-1 focus:ring-[#0f6885] focus:border-[#0f6885]"
              placeholder="Ex: T-Shirt Vintage"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-gray-700">Prix (TND)</label>
            <input
              type="number"
              value={formData.price}
              onChange={(e) => setFormData(prev => ({ ...prev, price: e.target.value }))}
              className="bg-white border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-medium focus:outline-none focus:ring-1 focus:ring-[#0f6885] focus:border-[#0f6885]"
              placeholder="Ex: 45"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-gray-700">Description</label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="bg-white border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-medium focus:outline-none focus:ring-1 focus:ring-[#0f6885] focus:border-[#0f6885] resize-y"
              placeholder="Description détaillée du produit..."
            />
          </div>

          <div className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3 border border-gray-200">
            <div>
              <p className="text-[13px] font-bold text-gray-700">Disponibilité</p>
              <p className="text-[11px] text-gray-500 mt-0.5">Si désactivé, l'IA refusera les commandes de ce produit</p>
            </div>
            <button
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, in_stock: !prev.in_stock }))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${formData.in_stock ? 'bg-emerald-500' : 'bg-gray-300'}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform ${formData.in_stock ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>

          <div className="pt-2 border-t border-gray-100">
            <h4 className="text-[13px] font-bold text-gray-700 mb-3">Attributs Personnalisés (Optionnel)</h4>
            <div className="flex flex-col gap-3">
              {customAttributes.map((attr, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <input
                    type="text"
                    value={attr.key}
                    onChange={(e) => {
                      const newAttrs = [...customAttributes];
                      newAttrs[index].key = e.target.value;
                      setCustomAttributes(newAttrs);
                    }}
                    placeholder="Ex: Couleur, Taille..."
                    className="flex-1 bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#0f6885]"
                  />
                  <input
                    type="text"
                    value={attr.value}
                    onChange={(e) => {
                      const newAttrs = [...customAttributes];
                      newAttrs[index].value = e.target.value;
                      setCustomAttributes(newAttrs);
                    }}
                    placeholder="Ex: Rouge, M..."
                    className="flex-1 bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#0f6885]"
                  />
                  <button
                    onClick={() => {
                      const newAttrs = [...customAttributes];
                      newAttrs.splice(index, 1);
                      setCustomAttributes(newAttrs);
                    }}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => setCustomAttributes([...customAttributes, { key: '', value: '' }])}
                className="self-start flex items-center gap-1.5 text-[13px] font-medium text-[#0f6885] hover:text-[#0c5973] px-2 py-1.5 rounded-lg hover:bg-[#0f6885]/5 transition-colors"
              >
                <Plus className="w-4 h-4" /> Ajouter un attribut
              </button>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 px-6 py-4 flex items-center justify-end gap-3 border-t border-gray-100">
          <button
            onClick={onClose}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving}
            className="px-5 py-2 text-sm font-bold text-white bg-[#0f6885] hover:bg-[#0c5973] rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {editingItem ? 'Mettre à jour' : 'Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  );
};
