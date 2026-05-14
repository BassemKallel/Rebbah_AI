import React from 'react';
import { Package, Edit2, Trash2 } from 'lucide-react';

interface ProductCardProps {
  item: any;
  viewMode?: 'grid' | 'list';
  onEdit: (item: any) => void;
  onDelete: (id: number) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ item, viewMode = 'grid', onEdit, onDelete }) => {
  const isList = viewMode === 'list';

  return (
    <div className={`bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all group flex ${isList ? 'flex-row items-stretch' : 'flex-col'}`}>
      <div className={`relative bg-gray-50 flex items-center justify-center overflow-hidden ${isList ? 'w-48 shrink-0 border-r border-gray-100' : 'h-48 border-b border-gray-100'}`}>
        {item.image_url ? (
          <img src={item.image_url} alt={item.metadata?.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
        ) : (
          <Package className="w-8 h-8 text-gray-300" />
        )}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-3">
          <button
            onClick={() => onEdit(item)}
            className="bg-white text-gray-800 p-2 rounded-lg shadow-sm hover:bg-gray-100 transition-colors"
            title="Modifier"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(item.id)}
            className="bg-red-50 text-red-600 p-2 rounded-lg shadow-sm hover:bg-red-100 transition-colors"
            title="Supprimer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col bg-white">
        <div className="flex items-center justify-between mb-1.5 gap-2">
          <h3 className="font-bold text-gray-900 text-[14px] leading-tight line-clamp-2">
            {item.metadata?.name || 'Produit sans nom'}
          </h3>
          {item.metadata?.price && (
            <div className="bg-gray-50 text-gray-900 font-bold text-[13px] px-2 py-0.5 rounded border border-gray-100 shrink-0">
              {item.metadata.price} TND
            </div>
          )}
        </div>
        <div className="mb-2">
          <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${item.metadata?.in_stock === false
            ? 'bg-red-50 text-red-600 border border-red-100'
            : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
            }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${item.metadata?.in_stock === false ? 'bg-red-500' : 'bg-emerald-500'}`} />
            {item.metadata?.in_stock === false ? 'Rupture de stock' : 'En stock'}
          </span>
        </div>
        <p className="text-[12px] text-gray-500 line-clamp-2 leading-snug mb-4">
          {item.metadata?.description || 'Aucune description disponible.'}
        </p>
        <div className="mt-auto pt-3 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[10px] font-medium text-gray-400">
            créé le {new Date(item.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
};
