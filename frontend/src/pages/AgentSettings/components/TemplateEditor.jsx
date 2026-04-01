import React, { useState, useEffect } from 'react';
import { Loader2, RotateCcw, Lock } from 'lucide-react';
import { useTemplates } from '../../../hooks/useTemplates';
import DynamicTemplate from './DynamicTemplate';
import CustomToggle from './CustomToggle';
import Toast from '../../../components/ui/Toast';

/**
 * TemplateEditor - Composant réutilisable pour gérer les templates.
 * Affiche le template système (read-only) et permet de créer/éditer un template custom.
 * * @param {Object} props
 * @param {string} props.category - Catégorie (response, missing_entity, order_confirmed, out_of_stock)
 * @param {string} props.subKey - Sous-clé (GREETING, size, with_ref, etc.)
 * @param {string} props.language - Langue (FR, AR, EN)
 * @param {string} props.shopId - Identifiant du shop
 * @param {string} props.token - Bearer token
 * @param {Array<string>} props.availableVariables - Variables disponibles pour ce template
 * @param {string} props.label - Label du template (optionnel)
 */
const TemplateEditor = ({
  category,
  subKey,
  language,
  shopId,
  token,
  availableVariables = [],
  label = 'Response Template'
}) => {
  // Fetch system templates (is_default=true, no shop_id filter)
  const systemFilters = { category, language, is_default: true };
  const { templates: systemTemplates, loading: loadingSystem } = useTemplates(systemFilters, token);

  // Fetch custom templates (for this shop)
  const customFilters = { category, language, shop_id: shopId };
  const { templates: customTemplates, loading: loadingCustom, create, update, remove } = useTemplates(customFilters, token);

  const [useCustom, setUseCustom] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState(null);

  const loading = loadingSystem || loadingCustom;

  // Find system and custom templates (Correction : utilisation de intent au lieu de sub_key)
  const systemTemplate = systemTemplates.find(t =>
    t.template_type === category &&
    t.intent === subKey &&
    t.language === language &&
    t.is_default === true
  );

  const customTemplate = customTemplates.find(t =>
    t.template_type === category &&
    t.intent === subKey &&
    t.language === language &&
    t.shop_id === shopId
  );

  // Update toggle based on custom template existence
  useEffect(() => {
    setUseCustom(!!customTemplate);
  }, [customTemplate]);

  const handleSave = async (templateContent) => {
    setIsSaving(true);
    setToast(null);

    // Correction : alignement strict avec les champs attendus par l'API
    const templateData = {
      template_type: category, // Utilisé par l'API au lieu de category
      intent: subKey,          // Utilisé par l'API au lieu de sub_key
      language,
      text: templateContent,   // Utilisé par l'API au lieu de content
      shop_id: shopId
    };

    let result;
    if (customTemplate) {
      // Update existing custom template
      result = await update(customTemplate.id, templateData);
    } else {
      // Create new custom template
      result = await create(templateData);
    }

    setIsSaving(false);

    if (result.success) {
      setToast({
        type: 'success',
        message: 'Template saved successfully!'
      });
    } else {
      setToast({
        type: 'error',
        message: result.error || 'Failed to save template'
      });
    }
  };

  const handleReset = async () => {
    if (!customTemplate) return;

    if (!window.confirm('Are you sure you want to reset to the default template? This will delete your custom template.')) {
      return;
    }

    setIsSaving(true);
    setToast(null);

    const result = await remove(customTemplate.id);

    setIsSaving(false);

    if (result.success) {
      setUseCustom(false);
      setToast({
        type: 'success',
        message: 'Reset to default template successfully!'
      });
    } else {
      setToast({
        type: 'error',
        message: result.error || 'Failed to reset template'
      });
    }
  };

  const handleToggle = (value) => {
    if (!value && customTemplate) {
      // User is turning off custom - ask for confirmation
      handleReset();
    } else {
      setUseCustom(value);
    }
  };

  // Format variables for DynamicTemplate (add curly braces if missing)
  const formattedVariables = availableVariables.map(v =>
    v.startsWith('{') ? v : `{${v}}`
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-6 h-6 text-[#0f6885] animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Section Header */}
      <div>
        <h3 className="text-base font-bold text-gray-800 mb-1">{label}</h3>
        <p className="text-sm text-gray-500">Default template from the system and your custom version</p>
      </div>

      {/* System Template (Read-only) */}
      <div className="border-2 border-gray-200 bg-gray-50 rounded-2xl p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-gray-500" />
            <h4 className="text-sm font-bold text-gray-700">System Template (Default)</h4>
          </div>
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Read-only</span>
        </div>

        {systemTemplate ? (
          <>
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              {/* Correction : utilisation de systemTemplate.text au lieu de systemTemplate.content */}
              <p className="text-gray-700 font-medium text-sm whitespace-pre-wrap">
                {systemTemplate.text}
              </p>
            </div>

            {systemTemplate.available_variables && systemTemplate.available_variables.length > 0 && (
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-xs font-semibold text-gray-500">Variables:</span>
                {systemTemplate.available_variables.map((variable, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-1 bg-gray-200 text-gray-600 text-xs font-semibold rounded-md"
                  >
                    {variable}
                  </span>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="text-gray-500 text-sm italic">No system template available for this configuration.</p>
        )}
      </div>

      {/* Custom Template Section */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-base font-bold text-gray-800">Custom Template</h4>
            <p className="text-sm text-gray-400 font-medium mt-0.5">
              Override the default template with your own
            </p>
          </div>
          <CustomToggle checked={useCustom} onChange={handleToggle} />
        </div>

        {useCustom && (
          <div className="flex flex-col gap-4 pt-3 border-t border-gray-100">
            {/* Correction : utilisation de .text au lieu de .content */}
            <DynamicTemplate
              initialValue={customTemplate?.text || systemTemplate?.text || ''}
              availableVars={formattedVariables}
              onSave={handleSave}
              isLoading={isSaving}
              label={label}
            />

            {customTemplate && (
              <div className="flex justify-start">
                <button
                  onClick={handleReset}
                  disabled={isSaving}
                  className="text-sm font-semibold text-gray-600 hover:text-[#0f6885] flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="w-4 h-4" />
                  Reset to Default
                </button>
              </div>
            )}
          </div>
        )}

        {!useCustom && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
            <p className="text-sm text-blue-800 font-medium">
              💡 Enable "Custom Template" to create your own personalized response that will override the system default.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TemplateEditor;