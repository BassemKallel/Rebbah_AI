import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Info, X } from 'lucide-react';

/**
 * Toast notification component.
 * Displays temporary notifications with auto-dismiss.
 * 
 * @param {Object} props
 * @param {string} props.message - Notification message
 * @param {string} props.type - Type: 'success' | 'error' | 'info'
 * @param {number} props.duration - Auto-dismiss duration in ms (default: 4000)
 * @param {function} props.onClose - Callback when toast closes
 */
const Toast = ({ message, type = 'info', duration = 4000, onClose }) => {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        if (duration > 0) {
            const timer = setTimeout(() => {
                setIsVisible(false);
                if (onClose) {
                    setTimeout(onClose, 300); // Wait for fade-out animation
                }
            }, duration);

            return () => clearTimeout(timer);
        }
    }, [duration, onClose]);

    const handleClose = () => {
        setIsVisible(false);
        if (onClose) {
            setTimeout(onClose, 300);
        }
    };

    const typeConfig = {
        success: {
            icon: <CheckCircle className="w-5 h-5" />,
            bgColor: 'bg-green-50',
            borderColor: 'border-green-500',
            textColor: 'text-green-800',
            iconColor: 'text-green-500'
        },
        error: {
            icon: <XCircle className="w-5 h-5" />,
            bgColor: 'bg-red-50',
            borderColor: 'border-red-500',
            textColor: 'text-red-800',
            iconColor: 'text-red-500'
        },
        info: {
            icon: <Info className="w-5 h-5" />,
            bgColor: 'bg-blue-50',
            borderColor: 'border-blue-500',
            textColor: 'text-blue-800',
            iconColor: 'text-blue-500'
        }
    };

    const config = typeConfig[type] || typeConfig.info;

    return (
        <div
            className={`
        fixed top-6 right-6 z-50 
        flex items-center gap-3 
        ${config.bgColor} ${config.textColor}
        border-l-4 ${config.borderColor}
        rounded-xl shadow-lg
        px-4 py-3 pr-12
        min-w-[320px] max-w-md
        transition-all duration-300
        ${isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}
      `}
            role="alert"
        >
            <div className={config.iconColor}>
                {config.icon}
            </div>

            <p className="text-sm font-semibold flex-1">
                {message}
            </p>

            <button
                onClick={handleClose}
                className={`
          absolute top-3 right-3
          ${config.textColor} hover:opacity-70
          transition-opacity
        `}
                aria-label="Close notification"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
};

/**
 * Toast container component for managing multiple toasts.
 * Use this to display multiple notifications stacked vertically.
 */
export const ToastContainer = ({ toasts = [], onRemove }) => {
    return (
        <div className="fixed top-6 right-6 z-50 flex flex-col gap-3">
            {toasts.map((toast, index) => (
                <Toast
                    key={toast.id || index}
                    message={toast.message}
                    type={toast.type}
                    duration={toast.duration}
                    onClose={() => onRemove && onRemove(toast.id || index)}
                />
            ))}
        </div>
    );
};

export default Toast;
