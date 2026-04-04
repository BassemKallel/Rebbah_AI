import React, { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import TemplateEditor from '../components/TemplateEditor';

const LANGUAGES = [
  { code: 'FR', label: 'French' },
  { code: 'AR', label: 'Arabic' },
  { code: 'EN', label: 'English' },
];

/**
 * ResponseIntent — Per-intent response template editor.
 */
const ResponseIntent = ({ intentKey, intentConfig }) => {
  const shopId = process.env.REACT_APP_SHOP_ID || '1LXybpj';
  const token = process.env.REACT_APP_SHOP_TOKEN;

  const [selectedLanguage, setSelectedLanguage] = useState('FR');

  // Convert kebab-case to SCREAMING_SNAKE_CASE for API
  const apiSubKey = intentKey.toUpperCase().replace(/-/g, '_');

  return (
    <div className="max-w-4xl">

      {/* ── Page Header ── */}
      <div className="flex items-start gap-3 mb-8">
        <div className="w-9 h-9 rounded-xl bg-[#eef6f9] flex items-center justify-center flex-shrink-0 mt-0.5">
          <MessageSquare className="w-4 h-4 text-[#0f6885]" />
        </div>
        <div>
          <h1 className="text-[22px] font-extrabold text-gray-800">
            {intentConfig.label}
          </h1>
          <p className="text-[14px] font-medium text-gray-400 mt-0.5">
            Customize how your AI responds to this intent across different languages
          </p>
          {/* Variable pills */}
          {intentConfig.vars && intentConfig.vars.length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs font-semibold text-gray-400">Variables:</span>
              {intentConfig.vars.map(v => (
                <code key={v} className="text-xs font-mono font-bold px-2 py-1 bg-[#eef6f9] text-[#0f6885] rounded-lg border border-[#d6ecf3]">
                  {`{${v}}`}
                </code>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Language Selector ── */}
      <div className="mb-6">
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

      {/* ── Template Editor ── */}
      <TemplateEditor
        key={`${apiSubKey}-${selectedLanguage}`}
        category="response"
        subKey={apiSubKey}
        language={selectedLanguage}
        shopId={shopId}
        token={token}
        availableVariables={intentConfig.vars || []}
        label={`${intentConfig.label} Response`}
      />
    </div>
  );
};

export default ResponseIntent;
