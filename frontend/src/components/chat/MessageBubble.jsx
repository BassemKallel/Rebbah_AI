import React from 'react';
import { Volume2, Copy, RefreshCw, ThumbsDown } from 'lucide-react';

const MessageBubble = ({ message }) => {
    const isUser = message.sender === 'user';

    return (
        <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-8 group`}>

            {/* AI Avatar */}
            {!isUser && (
                <div className="mr-3 flex-shrink-0 mt-1">
                    <div className="w-10 h-10 rounded-full bg-[#eef1f6] flex items-center justify-center text-[#185573] border-2 border-white shadow-sm transition-transform hover:scale-110">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-[22px] h-[22px]">
                            <rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>
                            <rect x="9" y="9" width="6" height="6"></rect>
                            <line x1="9" y1="1" x2="9" y2="4"></line>
                            <line x1="15" y1="1" x2="15" y2="4"></line>
                            <line x1="9" y1="20" x2="9" y2="23"></line>
                            <line x1="15" y1="20" x2="15" y2="23"></line>
                            <line x1="20" y1="9" x2="23" y2="9"></line>
                            <line x1="20" y1="14" x2="23" y2="14"></line>
                            <line x1="1" y1="9" x2="4" y2="9"></line>
                            <line x1="1" y1="14" x2="4" y2="14"></line>
                        </svg>
                    </div>
                </div>
            )}

            {/* Bubble Content */}
            <div className={`flex flex-col max-w-[85%] md:max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>

                {/* User Avatar & Content Container */}
                <div className={`flex ${isUser ? 'flex-row-reverse' : 'flex-row'} items-end gap-2 relative`}>

                    {/* User Avatar */}
                    {isUser && (
                        <div className="flex-shrink-0 mb-1 ml-2">
                            <img
                                src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                                alt="User"
                                className="w-8 h-8 rounded-full object-cover shadow-sm border-2 border-white"
                            />
                        </div>
                    )}

                    {/* Actual Bubble */}
                    <div
                        className={`relative rounded-3xl px-5 py-3.5 flex flex-col shadow-sm transition-shadow hover:shadow-md ${isUser
                            ? 'bg-[#0f6885] text-white rounded-br-sm'
                            : 'bg-white border border-gray-100 text-gray-800 rounded-bl-sm'
                            }`}
                    >
                        {/* Text Content */}
                        {message.text && (
                            <p className="text-[15.5px] leading-relaxed font-semibold tracking-wide">
                                {message.text}
                            </p>
                        )}

                        {/* Timestamp & Read Receipts */}
                        <div className={`flex items-center space-x-1 mt-2 md:mt-1 ${isUser ? 'justify-end text-blue-100' : 'justify-end text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity'}`}>
                            <span className="text-[11.5px] font-bold">{message.time}</span>
                            {isUser && (
                                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            )}
                        </div>
                    </div>
                </div>

                {/* AI Action Icons Footer */}
                {!isUser && (
                    <div className="flex items-center space-x-3 mt-2.5 ml-3 text-gray-400 opacity-60 group-hover:opacity-100 transition-opacity">
                        <button className="p-1 rounded-md hover:bg-gray-100 hover:text-indigo-600 transition-colors active:scale-95"><Volume2 className="w-4 h-4" /></button>
                        <button className="p-1 rounded-md hover:bg-gray-100 hover:text-indigo-600 transition-colors active:scale-95"><Copy className="w-4 h-4" /></button>
                        <button className="p-1 rounded-md hover:bg-gray-100 hover:text-indigo-600 transition-colors active:scale-95"><RefreshCw className="w-4 h-4" /></button>
                        <button className="p-1 rounded-md hover:bg-gray-100 hover:text-red-500 transition-colors active:scale-95"><ThumbsDown className="w-4 h-4" /></button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default MessageBubble;
