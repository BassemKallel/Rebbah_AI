import React, { useState } from 'react';
import { Smile, Mic, Send, Paperclip } from 'lucide-react';
import logoTiktak from '../../assets/images/logoTiktak.png';

const ChatInput = ({ onSendMessage }) => {
    const [message, setMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (message.trim()) {
            onSendMessage(message);
            setMessage('');
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="w-full mt-auto mb-6 px-4 pb-2 bg-transparent z-10 shrink-0">
            <form
                onSubmit={handleSubmit}
                className="relative flex items-center bg-white border border-gray-200 rounded-3xl p-2.5 shadow-[0_4px_20px_-8px_rgba(0,0,0,0.08)]"
            >
                {/* Attachment Button */}
                <button type="button" className="p-2.5 text-gray-400 hover:text-gray-600 transition-colors ml-1">
                    <Paperclip className="w-5 h-5 transform -rotate-45" />
                </button>

                {/* Input */}
                <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Message to Street Wear Agent..."
                    className="flex-1 bg-transparent border-none focus:outline-none focus:ring-0 text-gray-700 px-3 placeholder-gray-400 font-medium text-[15px] text-left"
                />

                {/* Right Actions */}
                <div className="flex items-center space-x-1.5 mr-1">
                    <button type="button" className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                        <Smile className="w-5 h-5" />
                    </button>
                    <button type="button" className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                        <Mic className="w-5 h-5" />
                    </button>
                    <button
                        type="submit"
                        disabled={!message.trim()}
                        className={`text-white rounded-[20px] px-5 py-2.5 ml-1 flex items-center justify-center transition-all shadow-sm ${message.trim()
                            ? 'bg-[#0f6885] hover:bg-[#0c5973] cursor-pointer hover:shadow-md active:scale-95'
                            : 'bg-[#a5c3cf] cursor-not-allowed'
                            }`}
                    >
                        <span className="font-bold text-[15px] mr-1.5">Send</span>
                        <Send className="w-4 h-4 ml-0.5" />
                    </button>
                </div>
            </form>

            {/* Footer text */}
            <div className="flex justify-center mt-4">
                <span className="text-gray-400 text-[13px] font-semibold flex items-center tracking-wide">
                    Powered By <img src={logoTiktak} alt="Tiktak Logo" className="h-4 mx-1.5 drop-shadow-sm" /> <span className="text-gray-500 font-bold ml-0.5">Tiktak PRO</span>
                </span>
            </div>
        </div>
    );
};

export default ChatInput;
