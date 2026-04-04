import React, { useEffect } from 'react';
import { Trash2, Loader } from 'lucide-react';
import type { Lead } from '../../types';

interface DeleteModalProps {
  lead: Lead;
  onClose: () => void;
  onConfirm: () => void;
  deleting: boolean;
}

const DeleteModal: React.FC<DeleteModalProps> = ({ lead, onClose, onConfirm, deleting }) => {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !deleting) onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose, deleting]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4"
      onClick={(e) => { if (e.target === e.currentTarget && !deleting) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
        <div className="flex flex-col items-center px-6 pt-8 pb-4 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mb-4">
            <Trash2 className="w-7 h-7 text-red-500" />
          </div>
          <h2 className="text-base font-bold text-gray-800 mb-1">Supprimer ce lead&nbsp;?</h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            Vous êtes sur le point de supprimer&nbsp;
            <span className="font-semibold text-gray-700">{lead.name || `#${lead.id}`}</span>.
            Cette action est irréversible.
          </p>
        </div>
        <div className="flex gap-2 px-6 pb-6 pt-2">
          <button onClick={onClose} disabled={deleting}
            className="flex-1 px-4 py-2.5 text-sm font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors disabled:opacity-50">
            Annuler
          </button>
          <button onClick={onConfirm} disabled={deleting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-red-500 hover:bg-red-600 rounded-xl transition-colors disabled:opacity-50">
            {deleting ? <Loader className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            {deleting ? 'Suppression…' : 'Supprimer'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DeleteModal;
