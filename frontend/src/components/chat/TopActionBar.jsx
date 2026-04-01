import React from 'react';
import { Sun, Moon, Search, ShoppingCart, Eye } from 'lucide-react';

const TopActionBar = () => {
    return (
        // Removed absolute positioning so it flows naturally in the flex container
        // when placed inside the Dashboard or Active Chat headers
        <div className="flex items-center justify-end w-full bg-transparent z-50">
            <div className="pointer-events-auto flex items-center space-x-2 md:space-x-4">
                {/* Theme Toggle */}
                <div className="flex items-center space-x-1 border border-gray-200 rounded-full p-0.5 bg-white shadow-sm hover:shadow transition-shadow">
                    <button className="p-1.5 rounded-full bg-[#f8f9fc] text-[#0f6885] transition-colors hover:scale-105 active:scale-95">
                        <Sun className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-800 transition-colors hover:scale-105 active:scale-95">
                        <Moon className="w-4 h-4" />
                    </button>
                </div>

                {/* Search */}
                <button className="p-2 rounded-full border border-gray-200 bg-white text-gray-500 hover:text-[#0f6885] hover:border-indigo-100 hover:bg-indigo-50 hover:shadow-sm transition-all active:scale-95">
                    <Search className="w-4 h-4" />
                </button>

                {/* Cart */}
                <button className="p-2 rounded-full border border-gray-200 bg-white text-gray-500 hover:text-[#0f6885] hover:border-indigo-100 hover:bg-indigo-50 hover:shadow-sm transition-all active:scale-95">
                    <ShoppingCart className="w-4 h-4" />
                </button>

                {/* View Shop */}
                <button className="flex items-center space-x-1.5 px-4 py-2 rounded-full border border-gray-200 bg-white text-gray-700 font-bold text-[13px] hover:bg-indigo-50 hover:text-[#0f6885] hover:border-indigo-100 hover:shadow-sm transition-all active:scale-95 group">
                    <Eye className="w-4 h-4 group-hover:text-[#0f6885]" />
                    <span className="hidden sm:inline">View Shop</span>
                </button>
            </div>
        </div>
    );
};

export default TopActionBar;
