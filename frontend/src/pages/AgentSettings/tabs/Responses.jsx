import React, { useState } from 'react';
import {
  Hand, ShoppingCart, Tag, Package, Truck, XCircle, HelpCircle, Info
} from 'lucide-react';
import TemplateEditor from '../components/TemplateEditor';

const INTENTS = [
  { key: 'GREETING', label: 'Greeting', Icon: Hand, vars: ['shop_name', 'ai_agent_name'] },
  { key: 'ORDER_PRODUCT', label: 'Order Product', Icon: ShoppingCart, vars: ['product'] },
  { key: 'ASK_PRICE', label: 'Ask Price', Icon: Tag, vars: ['product', 'price'] },
  { key: 'ASK_AVAILABILITY', label: 'Ask Availability', Icon: Package, vars: ['product'] },
  { key: 'ASK_DELIVERY', label: 'Ask Delivery', Icon: Truck, vars: ['shop_name'] },
  { key: 'CANCEL_ORDER', label: 'Cancel Order', Icon: XCircle, vars: [] },
  { key: 'UNKNOWN', label: 'Unknown Intent', Icon: HelpCircle, vars: [] },
  { key: 'INFORM_INFO', label: 'Inform Info', Icon: Info, vars: [] },
];

const LANGUAGES = [
  { code: 'FR', label: 'French' },
  { code: 'AR', label: 'Arabic' },
  { code: 'EN', label: 'English' },
];

const Responses = () => {
  const shopId = process.env.REACT_APP_SHOP_ID || '1LXybpj';
  const token = process.env.REACT_APP_SHOP_TOKEN;

  const [activeIntent, setActiveIntent] = useState(INTENTS[0].key);
  const [selectedLanguage, setSelectedLanguage] = useState('FR');

  const current = INTENTS.find(i => i.key === activeIntent) || INTENTS[0];
  const CurrentIcon = current.Icon;

  return (
    <div className="max-w-5xl">

      {/* ── Page Header ── */}
      <div className="mb-8">
        <h1 className="text-[22px] font-extrabold text-gray-800">Responses</h1>
        <p className="text-[14px] font-medium text-gray-400 mt-1">
          Customize what your AI says for each conversation intent
        </p>
      </div>

      <div className="flex gap-6">

        {/* ── Left Sidebar — Intent List ── */}
        <div className="w-52 flex-shrink-0 flex flex-col gap-5">
          <div>
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 px-1">
              Intent
            </p>
            <div className="flex flex-col gap-1">
              {INTENTS.map(intent => {
                const isActive = intent.key === activeIntent;
                const IntIcon = intent.Icon;
                return (
                  <button
                    key={intent.key}
                    onClick={() => setActiveIntent(intent.key)}
                    className={`
                      flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-left transition-all text-sm font-semibold
                      ${isActive
                        ? 'bg-[#0f6885] text-white shadow-sm'
                        : 'text-gray-500 hover:text-[#0f6885] hover:bg-[#eef6f9]'
                      }
                    `}
                  >
                    <IntIcon className="w-4 h-4 flex-shrink-0" />
                    <span>{intent.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Info card */}
          <div className="bg-[#eef6f9] border border-[#d6ecf3] rounded-xl p-3.5">
            <p className="text-xs font-bold text-[#0f6885] mb-1">About responses</p>
            <p className="text-xs text-[#0a4f66] leading-relaxed">
              Each intent maps to a specific customer interaction. Customize the AI reply for each one.
            </p>
          </div>
        </div>

        {/* ── Right Panel ── */}
        <div className="flex-1 min-w-0">

          {/* Intent Header Card */}
          <div className="bg-white border border-gray-100 shadow-sm rounded-2xl px-5 py-4 mb-5 flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#eef6f9] text-[#0f6885] flex items-center justify-center flex-shrink-0">
                <CurrentIcon className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Intent</p>
                <h2 className="text-base font-extrabold text-gray-800">{current.label}</h2>
              </div>
            </div>

            {current.vars.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap justify-end ml-4">
                <span className="text-xs font-semibold text-gray-400 mr-0.5">Variables:</span>
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
            key={`${activeIntent}-${selectedLanguage}`}
            category="response"
            subKey={activeIntent}
            language={selectedLanguage}
            shopId={shopId}
            token={token}
            availableVariables={current.vars}
            label={`${current.label} Response`}
          />
        </div>
      </div>
    </div>
  );
};

export default Responses;
