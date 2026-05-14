import React from 'react';
import { Box, Plus } from 'lucide-react';

interface ProductEmptyStateProps {
  onCreate: () => void;
}

export const ProductEmptyState: React.FC<ProductEmptyStateProps> = ({ onCreate }) => (
  <div className="bg-white border border-gray-200 border-dashed rounded-xl flex flex-col items-center justify-center py-24 shadow-sm">
    <div className="bg-gray-50 p-4 rounded-full mb-4">
      <Box className="w-8 h-8 text-gray-400" />
    </div>
    <h3 className="text-base font-bold text-gray-900 mb-1">Votre catalogue est vide</h3>
    <p className="text-gray-500 text-[13px] max-w-sm text-center mb-6">
      Ajoutez votre premier produit pour que l'IA puisse le recommander à vos clients.
    </p>
    <button onClick={onCreate} className="bg-[#0f6885] text-white font-bold text-sm px-5 py-2.5 rounded-lg flex items-center gap-2 hover:bg-[#0c5973] transition-all shadow-sm">
      <Plus className="w-4 h-4" /> Ajouter mon premier produit
    </button>
  </div>
);
