import React, { useState } from 'react';
import {
    ShoppingBag, Palette, Ruler, Hash, MapPin, Phone
} from 'lucide-react';
import TemplateEditor from '../components/TemplateEditor';

const ENTITIES = [
    { key: 'product', label: 'Product', Icon: ShoppingBag, vars: ['product'] },
    { key: 'color', label: 'Color', Icon: Palette, vars: ['color', 'product'] },
    { key: 'size', label: 'Size', Icon: Ruler, vars: ['size', 'product'] },
    { key: 'quantity', label: 'Quantity', Icon: Hash, vars: ['quantity', 'product'] },
    { key: 'address', label: 'Delivery Address', Icon: MapPin, vars: ['address'] },
    { key: 'phone_number', label: 'Phone Number', Icon: Phone, vars: [] },
];

const LANGUAGES = [
    { code: 'FR', label: 'French', flag: 'FR' },
    { code: 'AR', label: 'Arabic', flag: 'AR' },
    { code: 'EN', label: 'English', flag: 'EN' },
];

const MissingEntities = () => {
    const shopId = process.env.REACT_APP_SHOP_ID || '1LXybpj';
    const token = process.env.REACT_APP_SHOP_TOKEN;

    const [activeEntity, setActiveEntity] = useState(ENTITIES[0].key);
    const [selectedLanguage, setSelectedLanguage] = useState('FR');

    const current = ENTITIES.find(e => e.key === activeEntity) || ENTITIES[0];
    const CurrentIcon = current.Icon;

    return (
        <div className="max-w-5xl">

            {/* ── Page Header ── */}
            <div className="mb-8">
                <h1 className="text-[22px] font-extrabold text-gray-800">Missing Entities</h1>
                <p className="text-[14px] font-medium text-gray-400 mt-1">
                    Configure the questions your AI asks when order information is incomplete
                </p>
            </div>

            <div className="flex gap-6">

                {/* ── Left Sidebar — Entity List ── */}
                <div className="w-52 flex-shrink-0 flex flex-col gap-5">
                    <div>
                        <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 px-1">
                            Entity Type
                        </p>
                        <div className="flex flex-col gap-1">
                            {ENTITIES.map(entity => {
                                const isActive = entity.key === activeEntity;
                                const EntIcon = entity.Icon;
                                return (
                                    <button
                                        key={entity.key}
                                        onClick={() => setActiveEntity(entity.key)}
                                        className={`
                      flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-left transition-all text-sm font-semibold
                      ${isActive
                                                ? 'bg-[#0f6885] text-white shadow-sm'
                                                : 'text-gray-500 hover:text-[#0f6885] hover:bg-[#eef6f9]'
                                            }
                    `}
                                    >
                                        <EntIcon className="w-4 h-4 flex-shrink-0" />
                                        <span>{entity.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Info card */}
                    <div className="bg-[#eef6f9] border border-[#d6ecf3] rounded-xl p-3.5">
                        <p className="text-xs font-bold text-[#0f6885] mb-1">About missing entities</p>
                        <p className="text-xs text-[#0a4f66] leading-relaxed">
                            These messages are sent when the bot needs additional information to complete an order.
                        </p>
                    </div>
                </div>

                {/* ── Right Panel ── */}
                <div className="flex-1 min-w-0">

                    {/* Entity Header Card */}
                    <div className="bg-white border border-gray-100 shadow-sm rounded-2xl px-5 py-4 mb-5 flex items-start justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-[#eef6f9] text-[#0f6885] flex items-center justify-center flex-shrink-0">
                                <CurrentIcon className="w-4.5 h-4.5" />
                            </div>
                            <div>
                                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Entity</p>
                                <h2 className="text-base font-extrabold text-gray-800">{current.label}</h2>
                            </div>
                        </div>

                        {/* Variable badges */}
                        {current.vars.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap justify-end ml-4">
                                <span className="text-xs font-semibold text-gray-400 mr-1">Variables:</span>
                                {current.vars.map(v => (
                                    <code key={v} className="text-xs font-mono font-bold px-2 py-1 bg-[#eef6f9] text-[#0f6885] rounded-lg border border-[#d6ecf3]">
                                        {`{${v}}`}
                                    </code>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Language Selector */}
                    <div className="mb-5">
                        <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2.5">Language</p>
                        <div className="flex gap-2">
                            {LANGUAGES.map(lang => (
                                <button
                                    key={lang.code}
                                    onClick={() => setSelectedLanguage(lang.code)}
                                    className={`
                    px-4 py-2 rounded-xl font-bold text-sm transition-all border
                    ${selectedLanguage === lang.code
                                            ? 'bg-[#0f6885] text-white border-[#0f6885] shadow-sm'
                                            : 'bg-white text-gray-500 border-gray-200 hover:border-[#0f6885] hover:text-[#0f6885]'
                                        }
                  `}
                                >
                                    {lang.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Template Editor */}
                    <TemplateEditor
                        key={`${activeEntity}-${selectedLanguage}`}
                        category="missing_entity"
                        subKey={activeEntity}
                        language={selectedLanguage}
                        shopId={shopId}
                        token={token}
                        availableVariables={current.vars}
                        label={`${current.label} Question`}
                    />
                </div>
            </div>
        </div>
    );
};

export default MissingEntities;
